from __future__ import annotations
import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Account, Category, Transaction
from app.models.user import User
from app.schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])

EXPORT_COLUMNS = ["date", "amount", "description", "merchant", "category", "account", "status"]
ALLOWED_STATUSES = {"posted", "pending", "cleared"}


async def _owns_account(db: AsyncSession, user: User, account_id: int) -> Account | None:
    account = await db.get(Account, account_id)
    if account and account.user_id == user.id:
        return account
    return None


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if start:
        query = query.where(Transaction.date >= start)
    if end:
        query = query.where(Transaction.date <= end)
    query = query.limit(limit)

    result = await db.execute(query)
    txs = result.scalars().all()

    account_names = {}
    category_names = {}
    if txs:
        account_ids = {t.account_id for t in txs}
        category_ids = {t.category_id for t in txs if t.category_id}
        if account_ids:
            acc_result = await db.execute(select(Account).where(Account.id.in_(account_ids)))
            account_names = {a.id: a.name for a in acc_result.scalars()}
        if category_ids:
            cat_result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
            category_names = {c.id: c.name for c in cat_result.scalars()}

    out = []
    for t in txs:
        item = TransactionOut.model_validate(t)
        item.account_name = account_names.get(t.account_id)
        item.category_name = category_names.get(t.category_id)
        out.append(item)
    return out


@router.post("", response_model=TransactionOut)
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = await _owns_account(db, current_user, data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Category not found")
    tx = Transaction(**data.model_dump(), user_id=current_user.id)
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    item = TransactionOut.model_validate(tx)
    item.account_name = account.name
    if tx.category_id:
        category = await db.get(Category, tx.category_id)
        item.category_name = category.name if category else None
    return item


@router.put("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: int,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tx = await db.get(Transaction, transaction_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    account = await _owns_account(db, current_user, data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Category not found")
    for key, val in data.model_dump().items():
        setattr(tx, key, val)
    await db.commit()
    await db.refresh(tx)
    item = TransactionOut.model_validate(tx)
    item.account_name = account.name
    if tx.category_id:
        category = await db.get(Category, tx.category_id)
        item.category_name = category.name if category else None
    return item


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tx = await db.get(Transaction, transaction_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(tx)
    await db.commit()
    return {"status": "deleted"}


@router.get("/export")
async def export_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download all of the user's transactions as CSV.

    The amount column uses the same sign convention as the API: positive
    amounts are income, negative amounts are expenses. Exporting with these
    exact column names guarantees a round-trip through the import endpoint.
    """
    txs = (
        await db.execute(
            select(Transaction)
            .where(Transaction.user_id == current_user.id)
            .order_by(Transaction.date.asc())
        )
    ).scalars().all()

    account_names = {}
    category_names = {}
    if txs:
        account_ids = {t.account_id for t in txs}
        category_ids = {t.category_id for t in txs if t.category_id}
        if account_ids:
            account_names = {
                a.id: a.name
                for a in (await db.execute(select(Account).where(Account.id.in_(account_ids)))).scalars()
            }
        if category_ids:
            category_names = {
                c.id: c.name
                for c in (await db.execute(select(Category).where(Category.id.in_(category_ids)))).scalars()
            }

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for t in txs:
        writer.writerow(
            {
                "date": t.date.isoformat(),
                "amount": f"{t.amount:.2f}",
                "description": t.description or "",
                "merchant": t.merchant or "",
                "category": category_names.get(t.category_id) or "",
                "account": account_names.get(t.account_id) or "",
                "status": t.status,
            }
        )

    # StreamingResponse keeps the CSV off the event loop's memory for large exports.
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import transactions from a CSV upload.

    Expected columns: date (YYYY-MM-DD), amount (positive=income,
    negative=expense). Optional columns: description, merchant, category
    (matched by name, case-insensitive), account (matched by name,
    case-insensitive), status (posted/pending/cleared).

    Rows that fail validation are skipped and reported; valid rows are
    inserted. The import is per-row, so a malformed file never leaves the
    database half-written with silent errors.
    """
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")  # utf-8-sig strips a leading Excel BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded CSV")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "date" not in reader.fieldnames or "amount" not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail='CSV must have at least "date" and "amount" columns',
        )

    accounts = {a.name.lower(): a for a in (await db.execute(select(Account).where(Account.user_id == current_user.id))).scalars()}
    categories = {c.name.lower(): c for c in (await db.execute(select(Category).where(Category.user_id == current_user.id))).scalars()}
    if not accounts:
        raise HTTPException(status_code=400, detail="Create an account before importing transactions")

    created = 0
    errors = []
    for row_number, row in enumerate(reader, start=2):  # 1-based, header is row 1
        try:
            tx_date = date.fromisoformat(row["date"].strip())
            amount = float(row["amount"].strip())
            if not (abs(amount) >= 0.01):
                raise ValueError("amount must be non-zero")
        except (KeyError, ValueError) as exc:
            errors.append({"row": row_number, "error": f"invalid date/amount: {exc}"})
            continue

        status = (row.get("status") or "posted").strip().lower()
        if status not in ALLOWED_STATUSES:
            errors.append({"row": row_number, "error": f"invalid status '{status}'"})
            continue

        account_name = (row.get("account") or "").strip().lower()
        if account_name:
            account = accounts.get(account_name)
            if account is None:
                errors.append({"row": row_number, "error": f"unknown account '{account_name}'"})
                continue
        else:
            account = next(iter(accounts.values()))  # default to the first account

        category_name = (row.get("category") or "").strip().lower()
        if category_name:
            category = categories.get(category_name)
            if category is None:
                errors.append({"row": row_number, "error": f"unknown category '{category_name}'"})
                continue
        else:
            category = None

        tx = Transaction(
            user_id=current_user.id,
            account_id=account.id,
            category_id=category.id if category else None,
            date=tx_date,
            amount=amount,
            description=(row.get("description") or "").strip() or None,
            merchant=(row.get("merchant") or "").strip() or None,
            status=status,
        )
        db.add(tx)
        created += 1

    await db.commit()
    return {
        "created": created,
        "skipped": len(errors),
        "errors": errors[:50],  # cap the response payload on large imports
    }

"use client";

import { useState } from "react";
import type { ExpenseBody, GroupDetail } from "../lib/api";
import { formatMoney, parseAmount, splitEqual, toDecimal } from "../lib/money";

export default function ExpenseForm({
  group,
  user,
  disabled,
  saving,
  onSubmit,
}: {
  group: GroupDetail;
  user: string;
  disabled: boolean;
  saving: boolean;
  onSubmit: (body: ExpenseBody) => Promise<boolean>;
}) {
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [payer, setPayer] = useState(
    group.members.includes(user) ? user : group.members[0],
  );
  const [mode, setMode] = useState<"equal" | "exact">("equal");
  const [selected, setSelected] = useState(group.members);
  const [exact, setExact] = useState<Record<string, string>>({});
  const total = parseAmount(amount);
  const validTotal = total !== null && total > 0n;
  const members = group.members.filter((member) => selected.includes(member));
  const allocations =
    mode === "equal" && validTotal && members.length
      ? splitEqual(total, members)
      : {};
  const exactValues = members.map((member) => parseAmount(exact[member] ?? ""));
  const validShares = exactValues.every((value) => value !== null);
  const invalidShares = members.some(
    (member, index) =>
      (exact[member] ?? "") !== "" && exactValues[index] === null,
  );
  const allocated = exactValues.reduce<bigint>(
    (sum, value) => sum + (value ?? 0n),
    0n,
  );
  const remaining = total === null ? null : total - allocated;
  const ready =
    !!description.trim() &&
    validTotal &&
    members.length > 0 &&
    (mode === "equal" || (validShares && remaining === 0n));
  const reason = !description.trim()
    ? "เพิ่มรายละเอียดรายการก่อนบันทึก"
    : !validTotal
      ? "ระบุยอดบิลมากกว่า 0 และทศนิยมไม่เกิน 2 ตำแหน่ง"
      : !members.length
        ? "เลือกผู้ร่วมหารอย่างน้อย 1 คน"
        : mode === "exact" && invalidShares
          ? "จำนวนแบ่งต้องเป็นตัวเลขตั้งแต่ 0 และทศนิยมไม่เกิน 2 ตำแหน่ง"
          : mode === "exact" && !validShares
            ? "กรอกจำนวนของผู้ร่วมหารให้ครบ ใส่ 0 ได้"
            : !ready
              ? "ยอดแบ่งต้องรวมเท่ากับยอดบิล"
              : "ตรวจส่วนแบ่งเรียบร้อยแล้ว บันทึกได้เลย";

  return (
    <section className="entry-panel" aria-labelledby="entry-title">
      <div className="section-heading">
        <div>
          <h2 id="entry-title">เพิ่มค่าใช้จ่าย</h2>
          <p>ใครออกให้ ใครหารบ้าง เช็กได้ก่อนบันทึก</p>
        </div>
        <span className="unit-tag">THB</span>
      </div>
      <form
        data-testid="expense-form"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!ready || disabled) return;
          const body: ExpenseBody = {
            description: description.trim(),
            paid_by: payer,
            amount: toDecimal(total!),
            split:
              mode === "equal"
                ? { type: "equal", members }
                : {
                    type: "exact",
                    shares: Object.fromEntries(
                      members.map((member) => [
                        member,
                        toDecimal(parseAmount(exact[member])!),
                      ]),
                    ),
                  },
          };
          if (await onSubmit(body)) {
            setDescription("");
            setAmount("");
            setExact({});
          }
        }}
      >
        <fieldset disabled={disabled} className="form-fields">
          <label className="field">
            รายละเอียด
            <input
              name="description"
              required
              maxLength={500}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="เช่น มื้อเย็นกับเพื่อน"
              autoComplete="off"
            />
          </label>
          <div className="amount-payer">
            <label className="field">
              จำนวนเงิน (บาท)
              <input
                className="amount-input"
                name="amount"
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0.00"
                autoComplete="off"
                aria-invalid={amount !== "" && !validTotal}
                aria-describedby="amount-help"
              />
            </label>
            <label className="field">
              จ่ายโดย
              <select
                aria-label="จ่ายโดย"
                value={payer}
                onChange={(event) => setPayer(event.target.value)}
              >
                {group.members.map((member) => (
                  <option key={member} value={member}>
                    {member}
                    {member === user ? " (คุณ)" : ""}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p
            id="amount-help"
            className={
              amount !== "" && !validTotal ? "field-error" : "field-hint"
            }
          >
            {amount !== "" && !validTotal
              ? "ใช้ตัวเลขมากกว่า 0 ไม่เกิน 9,999,999,999.99 และทศนิยมไม่เกิน 2 ตำแหน่ง"
              : "ใส่ตัวเลข เช่น 100.00 โดยไม่ต้องใส่เครื่องหมายคั่นหลักพัน"}
          </p>
          <fieldset className="split-field">
            <legend>แบ่งกันแบบไหน</legend>
            <div className="split-options">
              <label className="choice">
                <input
                  type="radio"
                  name="split-mode"
                  checked={mode === "equal"}
                  onChange={() => setMode("equal")}
                />
                หารเท่ากัน
              </label>
              <label className="choice">
                <input
                  type="radio"
                  name="split-mode"
                  checked={mode === "exact"}
                  onChange={() => setMode("exact")}
                />
                กำหนดจำนวนเอง
              </label>
            </div>
          </fieldset>
          <div className="allocation-heading">
            <span>ผู้ร่วมหาร</span>
            <span>{members.length} คน</span>
          </div>
          <div className="allocation-list">
            {group.members.map((member) => {
              const checked = selected.includes(member);
              return (
                <div
                  className={`allocation-row ${checked ? "is-selected" : ""}`}
                  key={member}
                >
                  <label className="member-check">
                    <input
                      type="checkbox"
                      aria-label={member}
                      checked={checked}
                      onChange={() =>
                        setSelected(
                          checked
                            ? selected.filter((name) => name !== member)
                            : [...selected, member],
                        )
                      }
                    />
                    <span className="avatar" aria-hidden="true">
                      {member[0].toUpperCase()}
                    </span>
                    <span>
                      {member}
                      {member === user && <small>คุณ</small>}
                    </span>
                  </label>
                  {mode === "exact" && checked ? (
                    <label className="share-input">
                      <span className="sr-only">จำนวนของ {member}</span>
                      <input
                        aria-label={`จำนวนของ ${member} (บาท)`}
                        inputMode="decimal"
                        value={exact[member] ?? ""}
                        onChange={(event) =>
                          setExact({ ...exact, [member]: event.target.value })
                        }
                        placeholder="0.00"
                        aria-invalid={
                          !!exact[member] && parseAmount(exact[member]) === null
                        }
                        aria-describedby="exact-help"
                      />
                      <span>บาท</span>
                    </label>
                  ) : (
                    <span
                      className="money allocation-money"
                      data-testid={`preview-${member}`}
                    >
                      {checked && validTotal
                        ? formatMoney(allocations[member] ?? 0n)
                        : "—"}
                      <small>บาท</small>
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          {mode === "equal" ? (
            <p className="field-hint">
              เศษสตางค์จะแจกตามลำดับผู้ร่วมหารจากบนลงล่าง
            </p>
          ) : (
            <>
              <p
                id="exact-help"
                className={invalidShares ? "field-error" : "field-hint"}
              >
                จำนวนของแต่ละคนใส่ 0 ได้ ใช้ตัวเลขไม่เกิน 9,999,999,999.99
                และทศนิยมไม่เกิน 2 ตำแหน่ง ไม่ใส่เครื่องหมายคั่นหลักพัน
              </p>
              <div
                className={`remainder ${remaining !== 0n || !validShares ? "is-incomplete" : ""}`}
                role="status"
              >
                <span>
                  {remaining !== null && remaining < 0n
                    ? "แบ่งเกินไป"
                    : "ยังต้องแบ่งอีก"}
                </span>
                <strong className="money">
                  {remaining === null || invalidShares
                    ? "—"
                    : formatMoney(remaining < 0n ? -remaining : remaining)}{" "}
                  บาท
                </strong>
                {!validShares && (
                  <small>
                    {invalidShares
                      ? "แก้รูปแบบจำนวนแบ่งให้ถูกต้อง"
                      : "กรอกจำนวนของผู้ร่วมหารให้ครบ"}
                  </small>
                )}
              </div>
            </>
          )}
        </fieldset>
        <div className="form-bottom">
          <p className="field-hint" id="submit-help">
            {reason}
          </p>
          <button
            className="button primary"
            type="submit"
            disabled={!ready || disabled}
            aria-describedby="submit-help"
          >
            {saving ? "กำลังบันทึก…" : "บันทึกค่าใช้จ่าย"}
            <span aria-hidden="true">↗</span>
          </button>
        </div>
      </form>
    </section>
  );
}

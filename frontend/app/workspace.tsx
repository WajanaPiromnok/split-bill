"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import ExpenseForm from "./expense-form";
import {
  api,
  ApiError,
  errorMessage,
  type Expense,
  type ExpenseBody,
  type Group,
  type GroupDetail,
  type PendingExpense,
} from "../lib/api";
import { formatMoney, parseBalance } from "../lib/money";
import { decodePending, PENDING_KEY } from "../lib/pending";

const USERS = ["alice", "bob", "carol", "dan"];
type Snapshot = {
  group: GroupDetail;
  expenses: Expense[];
  balances: Record<string, string>;
};

export default function Workspace() {
  const [user, setUser] = useState("alice");
  const [groupId, setGroupId] = useState<number | null>(null);
  const [groupsState, setGroupsState] = useState<{
    user: string;
    groups: Group[];
  } | null>(null);
  const [groupsError, setGroupsError] = useState("");
  const [groupsVersion, setGroupsVersion] = useState(0);
  const [pending, setPending] = useState<PendingExpense | null>(null);
  const [restored, setRestored] = useState(false);
  const [storageError, setStorageError] = useState("");

  useEffect(() => {
    // sessionStorage is tab-local and unavailable during server rendering.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRestored(true);
    try {
      const raw = sessionStorage.getItem(PENDING_KEY);
      const saved = decodePending(raw);
      if (raw && !saved)
        setStorageError(
          "ข้อมูลรายการที่รอส่งไม่สมบูรณ์ กรุณาตรวจรายการในกลุ่มก่อนเพิ่มบิลใหม่",
        );
      if (saved) {
        setPending(saved);
        setUser(saved.user);
        setGroupId(saved.group);
      }
    } catch {
      setStorageError(
        "เบราว์เซอร์ไม่อนุญาตให้เก็บรายการรอส่ง กรุณาอนุญาตพื้นที่จัดเก็บก่อนเพิ่มค่าใช้จ่าย",
      );
    }
  }, []);

  useEffect(() => {
    if (!restored) return;
    const controller = new AbortController();
    api<Group[]>("/groups", user, { signal: controller.signal })
      .then((groups) => {
        if (controller.signal.aborted) return;
        setGroupsState({ user, groups });
        setGroupsError("");
        setGroupId((current) =>
          pending?.user === user
            ? pending.group
            : groups.some((group) => group.id === current)
              ? current
              : (groups[0]?.id ?? null),
        );
      })
      .catch((error) => {
        if (!controller.signal.aborted) setGroupsError(errorMessage(error));
      });
    return () => controller.abort();
  }, [user, groupsVersion, restored, pending?.user, pending?.group]);

  const groups = groupsState?.user === user ? groupsState.groups : null;
  function updatePending(value: PendingExpense | null) {
    if (value) sessionStorage.setItem(PENDING_KEY, JSON.stringify(value));
    else {
      try {
        sessionStorage.removeItem(PENDING_KEY);
      } catch {
        /* Replaying a retained key remains safe. */
      }
    }
    setPending(value);
  }

  return (
    <>
      <a className="skip-link" href="#workspace">
        ข้ามไปเนื้อหา
      </a>
      <header className="topbar">
        <a href="#workspace" className="brand" aria-label="SplitBill หน้าหลัก">
          <Image
            className="brand-mark"
            src="/icon.svg"
            width={43}
            height={43}
            alt=""
            unoptimized
          />
          <span>
            SplitBill<span className="brand-caption">แบ่งบิลให้ลงตัว</span>
          </span>
        </a>
        <label className="user-control">
          <span>กำลังใช้งานเป็น</span>
          <select
            aria-label="ผู้ใช้"
            value={user}
            disabled={!!pending}
            onChange={(event) => {
              setUser(event.target.value);
              setGroupId(null);
              setGroupsState(null);
              setGroupsError("");
            }}
          >
            {USERS.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
      </header>
      <main id="workspace" className="page-shell">
        <div className="group-heading">
          <div>
            <p className="context-label">ค่าใช้จ่ายของกลุ่ม</p>
            <h1>
              {groups?.find((group) => group.id === groupId)?.name ??
                (groups ? "เลือกกลุ่มของคุณ" : "มาแบ่งบิลกัน")}
            </h1>
          </div>
          <label className="group-control">
            <span>กลุ่ม</span>
            <select
              aria-label="กลุ่ม"
              value={groupId ?? ""}
              disabled={!groups || !!pending}
              onChange={(event) => setGroupId(Number(event.target.value))}
            >
              {!groups?.length && (
                <option value="">
                  {groups ? "ยังไม่มีกลุ่ม" : "กำลังโหลดกลุ่ม…"}
                </option>
              )}
              {pending &&
                !groups?.some((group) => group.id === pending.group) && (
                  <option value={pending.group}>
                    กลุ่ม #{pending.group} · รายการรอยืนยัน
                  </option>
                )}
              {groups?.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {storageError && (
          <div className="notice error" role="alert">
            <p>{storageError}</p>
            <button
              className="button secondary"
              onClick={() => {
                try {
                  sessionStorage.removeItem(PENDING_KEY);
                  setStorageError("");
                } catch {
                  /* Keep the warning until storage is available. */
                }
              }}
            >
              ตรวจรายการแล้ว เริ่มบิลใหม่
            </button>
          </div>
        )}
        {groupsError && (
          <div className="notice error" role="alert">
            <p>{groupsError}</p>
            <button
              className="button secondary"
              onClick={() => {
                setGroupsError("");
                setGroupsVersion((value) => value + 1);
              }}
            >
              โหลดกลุ่มอีกครั้ง
            </button>
          </div>
        )}
        {!groups && !groupsError && <Loading />}
        {groups?.length === 0 && !pending && (
          <section className="empty-state">
            <h2>ยังไม่มีกลุ่มสำหรับ {user}</h2>
            <p>เลือกผู้ใช้อื่นเพื่อดูกลุ่มที่เข้าถึงได้</p>
          </section>
        )}
        {restored && groupId !== null && (
          <GroupWorkspace
            key={`${user}:${groupId}`}
            user={user}
            groupId={groupId}
            pending={pending}
            updatePending={updatePending}
            storageError={!!storageError}
          />
        )}
      </main>
      <footer className="page-footer">
        <span>SplitBill</span>
        <span>เห็นส่วนแบ่งชัด ครบทุกสตางค์</span>
      </footer>
    </>
  );
}

function Loading() {
  return (
    <div className="loading-state" role="status">
      <span className="sr-only">กำลังโหลดข้อมูล…</span>
      <div className="skeleton" />
      <div className="skeleton short" />
      <div className="skeleton" />
    </div>
  );
}

function GroupWorkspace({
  user,
  groupId,
  pending,
  updatePending,
  storageError,
}: {
  user: string;
  groupId: number;
  pending: PendingExpense | null;
  updatePending: (value: PendingExpense | null) => void;
  storageError: boolean;
}) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loadError, setLoadError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formVersion, setFormVersion] = useState(0);
  const [notice, setNotice] = useState("");
  const [actionError, setActionError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const busy = useRef(false);
  const loadSequence = useRef(0);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const deleteTrigger = useRef<HTMLButtonElement | null>(null);
  const path = `/groups/${groupId}`;

  async function fetchSnapshot(signal?: AbortSignal): Promise<Snapshot> {
    const [group, expenses, balances] = await Promise.all([
      api<GroupDetail>(path, user, { signal }),
      api<Expense[]>(`${path}/expenses`, user, { signal }),
      api<Record<string, string>>(`${path}/balances`, user, { signal }),
    ]);
    return { group, expenses, balances };
  }

  useEffect(() => {
    const controller = new AbortController();
    const version = ++loadSequence.current;
    fetchSnapshot(controller.signal)
      .then((data) => {
        if (version === loadSequence.current && !controller.signal.aborted) {
          setSnapshot(data);
          setLoadError("");
        }
      })
      .catch((error) => {
        if (version === loadSequence.current && !controller.signal.aborted)
          setLoadError(errorMessage(error));
      });
    return () => controller.abort();
    // This component is remounted for each user/group pair.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (confirmDelete !== null) confirmButton.current?.focus();
  }, [confirmDelete]);

  async function refresh() {
    setRefreshing(true);
    setLoadError("");
    const version = ++loadSequence.current;
    try {
      const data = await fetchSnapshot();
      if (version === loadSequence.current) setSnapshot(data);
    } catch (error) {
      if (version === loadSequence.current) setLoadError(errorMessage(error));
    } finally {
      if (version === loadSequence.current) setRefreshing(false);
    }
  }

  async function send(intent: PendingExpense): Promise<boolean> {
    setSaving(true);
    setNotice("");
    setActionError("");
    try {
      const expense = await api<Expense>(
        `/groups/${intent.group}/expenses`,
        intent.user,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": intent.key,
          },
          body: JSON.stringify(intent.body),
        },
      );
      updatePending(null);
      setFormVersion((version) => version + 1);
      setNotice(
        expense.deleted
          ? "รายการเดิมถูกลบแล้ว จึงไม่นำกลับมาคิดยอด"
          : `บันทึก “${expense.description}” เรียบร้อยแล้ว`,
      );
      await refresh();
      return true;
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status >= 400 &&
        error.status < 500
      )
        updatePending(null);
      setActionError(errorMessage(error));
      return false;
    } finally {
      setSaving(false);
      busy.current = false;
    }
  }

  async function submit(body: ExpenseBody) {
    if (busy.current || pending) return false;
    busy.current = true;
    const intent = { key: crypto.randomUUID(), user, group: groupId, body };
    try {
      updatePending(intent);
    } catch {
      setActionError(
        "เก็บรายการรอส่งในเบราว์เซอร์ไม่ได้ ยังไม่ได้ส่งบิล กรุณาอนุญาตพื้นที่จัดเก็บแล้วลองอีกครั้ง",
      );
      busy.current = false;
      return false;
    }
    return send(intent);
  }

  return (
    <>
      <div className="feedback" aria-live="polite" aria-atomic="true">
        {notice && <div className="notice success">{notice}</div>}
      </div>
      {actionError && (
        <div className="notice error" role="alert">
          {actionError}
        </div>
      )}
      {pending && (
        <section className="pending-notice" aria-labelledby="pending-title">
          <div>
            <h2 id="pending-title">
              {saving ? "กำลังยืนยันรายการ…" : "มีรายการที่ยังรอยืนยัน"}
            </h2>
            <p>
              “{pending.body.description}” · {formatMoney(pending.body.amount)}{" "}
              บาท · {pending.user}
            </p>
            <p>
              หากการเชื่อมต่อขัดข้อง ให้ส่งรายการเดิมอีกครั้ง
              ระบบจะตรวจรายการซ้ำให้ ก่อนเริ่มบิลใหม่
            </p>
          </div>
          <button
            className="button primary"
            disabled={saving}
            onClick={() => {
              if (busy.current) return;
              busy.current = true;
              void send(pending);
            }}
          >
            ลองส่งรายการเดิมอีกครั้ง
          </button>
        </section>
      )}
      {loadError && (
        <div className="notice error" role="alert">
          <p>
            {notice
              ? "บันทึกการเปลี่ยนแปลงแล้ว แต่ยังโหลดข้อมูลล่าสุดไม่ได้ — "
              : ""}
            {loadError}
          </p>
          <button
            className="button secondary"
            disabled={refreshing}
            onClick={() => void refresh()}
          >
            โหลดข้อมูลล่าสุด
          </button>
        </div>
      )}
      {!snapshot && !loadError && <Loading />}
      {snapshot && (
        <>
          <div className="workspace-grid" aria-busy={refreshing}>
            <ExpenseForm
              key={formVersion}
              group={snapshot.group}
              user={user}
              disabled={
                !!pending || saving || deleting !== null || storageError
              }
              saving={saving}
              onSubmit={submit}
            />
            <aside
              className="balance-panel"
              role="region"
              aria-label="ยอดสุทธิของสมาชิก"
            >
              <div className="section-heading">
                <div>
                  <h2>ยอดสุทธิของสมาชิก</h2>
                  <p>จ่ายไป − ส่วนที่ต้องรับผิดชอบ</p>
                </div>
              </div>
              <div className="balance-list">
                {snapshot.group.members.map((member) => {
                  const value = snapshot.balances[member];
                  const satang = parseBalance(value);
                  const direction =
                    satang === null
                      ? "รอข้อมูล"
                      : satang > 0n
                        ? "ต้องได้รับคืน"
                        : satang < 0n
                          ? "ต้องจ่ายคืน"
                          : "ยอดสุทธิเป็นศูนย์";
                  return (
                    <div className="balance-row" key={member}>
                      <span className="avatar" aria-hidden="true">
                        {member[0].toUpperCase()}
                      </span>
                      <div className="balance-person">
                        <strong>
                          {member}
                          {member === user && <small>คุณ</small>}
                        </strong>
                        <span>{direction}</span>
                      </div>
                      <strong
                        className={`money balance-value ${satang !== null && satang < 0n ? "negative" : satang !== null && satang > 0n ? "positive" : ""}`}
                      >
                        {satang !== null && satang > 0n ? "+" : ""}
                        {formatMoney(value)}
                        <small>บาท</small>
                      </strong>
                    </div>
                  );
                })}
              </div>
              <div className="balance-explainer">
                <span className="small-symbol" aria-hidden="true">
                  =
                </span>
                <p>
                  ยอดรวมของทุกคนเท่ากับ 0.00 บาท
                  <br />
                  ตัวเลขนี้เป็นยอดสุทธิ ยังไม่ได้ระบุการโอนเงินระหว่างสมาชิก
                </p>
              </div>
              <div className="group-members">
                <h3>หารด้วยกันในกลุ่มนี้</h3>
                <div className="member-chips">
                  {snapshot.group.members.map((member) => (
                    <span key={member}>{member}</span>
                  ))}
                </div>
                <p>เห็นข้อมูลได้เฉพาะสมาชิกของกลุ่ม</p>
              </div>
            </aside>
          </div>
          <section
            className="expenses-section"
            aria-labelledby="expenses-title"
          >
            <div className="section-heading">
              <div>
                <h2 id="expenses-title" tabIndex={-1}>
                  รายการค่าใช้จ่าย{" "}
                  <span className="count">{snapshot.expenses.length}</span>
                </h2>
                <p>รายการล่าสุดอยู่ด้านบน</p>
              </div>
              <button
                className="button secondary compact"
                disabled={refreshing || saving || deleting !== null}
                onClick={() => void refresh()}
              >
                {refreshing ? "กำลังโหลด…" : "รีเฟรชรายการ"}
              </button>
            </div>
            {snapshot.expenses.length === 0 ? (
              <div className="empty-state">
                <span className="empty-symbol" aria-hidden="true">
                  ÷
                </span>
                <h3>บิลแรก เริ่มจากใครดี?</h3>
                <p>
                  เพิ่มค่าอาหาร ค่ารถ หรือค่าใช้จ่ายที่ออกให้เพื่อน
                  <br />
                  ส่วนแบ่งและยอดสุทธิจะอยู่ตรงนี้
                </p>
                <a href="#entry-title">
                  ไปเพิ่มค่าใช้จ่าย <span aria-hidden="true">↑</span>
                </a>
              </div>
            ) : (
              <div className="expense-list">
                {snapshot.expenses.map((expense) => (
                  <article
                    data-testid="expense-row"
                    className="expense-row"
                    key={expense.id}
                  >
                    <div className="expense-icon" aria-hidden="true">
                      ÷
                    </div>
                    <div className="expense-body">
                      <h3>{expense.description}</h3>
                      <p>
                        <span>{expense.paid_by} จ่ายให้ก่อน</span>
                        <span className="dot" aria-hidden="true">
                          ·
                        </span>
                        <time dateTime={expense.created_at}>
                          {new Intl.DateTimeFormat("th-TH", {
                            day: "numeric",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          }).format(new Date(expense.created_at))}
                        </time>
                      </p>
                      <details>
                        <summary>
                          ดูส่วนแบ่ง · {Object.keys(expense.shares).length} คน ·{" "}
                          {expense.split_type === "equal"
                            ? "หารเท่ากัน"
                            : "กำหนดจำนวนเอง"}
                        </summary>
                        <dl className="share-details">
                          {Object.entries(expense.shares).map(
                            ([member, value]) => (
                              <div key={member}>
                                <dt>{member}</dt>
                                <dd className="money">
                                  {formatMoney(value)} บาท
                                </dd>
                              </div>
                            ),
                          )}
                        </dl>
                      </details>
                    </div>
                    <div className="expense-amount">
                      <strong className="money">
                        {formatMoney(expense.amount)}
                      </strong>
                      <span>บาท</span>
                    </div>
                    <div className="expense-actions">
                      {expense.paid_by === user ? (
                        <button
                          className="delete-button"
                          aria-label={`ลบ ${expense.description}`}
                          disabled={!!pending || deleting !== null}
                          onClick={(event) => {
                            deleteTrigger.current = event.currentTarget;
                            setConfirmDelete(expense.id);
                          }}
                        >
                          ลบ
                        </button>
                      ) : (
                        <span className="payer-only">ลบได้โดยผู้จ่าย</span>
                      )}
                    </div>
                    {confirmDelete === expense.id && (
                      <div
                        className="delete-confirm"
                        role="group"
                        aria-label={`ยืนยันลบ ${expense.description}`}
                      >
                        <p>
                          ลบ “{expense.description}” ออกจากรายการและยอดสุทธิ?
                        </p>
                        <div>
                          <button
                            className="button secondary compact"
                            ref={confirmButton}
                            disabled={deleting !== null}
                            onClick={() => {
                              setConfirmDelete(null);
                              deleteTrigger.current?.focus();
                            }}
                          >
                            ยกเลิก
                          </button>
                          <button
                            className="button destructive compact"
                            disabled={deleting !== null}
                            onClick={async () => {
                              if (busy.current) return;
                              busy.current = true;
                              setDeleting(expense.id);
                              setActionError("");
                              setNotice("");
                              const heading =
                                document.getElementById("expenses-title");
                              try {
                                await api<void>(
                                  `${path}/expenses/${expense.id}`,
                                  user,
                                  { method: "DELETE" },
                                );
                                setConfirmDelete(null);
                                setNotice(`ลบ “${expense.description}” แล้ว`);
                                await refresh();
                                if (heading?.isConnected) heading.focus();
                              } catch (error) {
                                setActionError(errorMessage(error));
                              } finally {
                                busy.current = false;
                                setDeleting(null);
                              }
                            }}
                          >
                            {deleting === expense.id ? "กำลังลบ…" : "ยืนยันลบ"}
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}

"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import Image from "next/image";
import ExpenseForm, { type ExpenseFormHandle } from "./expense-form";
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
const PROFILE_KEY = "splitbill.user.v1";
type LeaveGuard = (
  next: () => void,
  destination: "profile" | "group",
  trigger: HTMLElement,
) => void;
type Snapshot = {
  group: GroupDetail;
  expenses: Expense[];
  balances: Record<string, string>;
};

export default function Workspace() {
  const [user, setUser] = useState<string | null>(null);
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
  const [profileError, setProfileError] = useState("");
  const [working, setWorking] = useState(false);
  const mutationBusyRef = useRef(false);
  const exitGuardRef = useRef<LeaveGuard | null>(null);
  const entryHeading = useRef<HTMLHeadingElement>(null);
  const focusEntry = useRef(false);
  const groupHeading = useRef<HTMLHeadingElement>(null);
  const focusGroup = useRef(false);

  useEffect(() => {
    // sessionStorage is tab-local and unavailable during server rendering.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRestored(true);
    try {
      const raw = sessionStorage.getItem(PENDING_KEY);
      const saved = decodePending(raw);
      if (raw && !saved)
        setStorageError(
          "อ่านข้อมูลรายการรอส่งไม่ได้ กรุณาตรวจรายการในกลุ่มก่อนเพิ่มบิลใหม่",
        );
      if (saved) {
        setPending(saved);
        setUser(saved.user);
        setGroupId(saved.group);
        try {
          sessionStorage.setItem(PROFILE_KEY, saved.user);
        } catch {
          setProfileError(
            "เบราว์เซอร์จำผู้ใช้เดิมไม่ได้ รายการรอยืนยันยังถูกเก็บไว้ กรุณาตรวจการตั้งค่าการเก็บข้อมูลแล้วลองส่งรายการเดิมอีกครั้ง",
          );
        }
      } else {
        const profile = sessionStorage.getItem(PROFILE_KEY);
        if (profile && USERS.includes(profile)) setUser(profile);
      }
    } catch {
      setStorageError(
        "เข้าถึงข้อมูลที่เก็บในเบราว์เซอร์ไม่ได้ กรุณาตรวจการตั้งค่าการเก็บข้อมูลก่อนเพิ่มค่าใช้จ่าย",
      );
    }
  }, []);

  useEffect(() => {
    if (!restored || user === null) return;
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
              : groups.length === 1
                ? groups[0].id
                : null,
        );
      })
      .catch((error) => {
        if (!controller.signal.aborted) setGroupsError(errorMessage(error));
      });
    return () => controller.abort();
  }, [user, groupsVersion, restored, pending?.user, pending?.group]);

  useEffect(() => {
    if (restored && user === null && focusEntry.current) {
      entryHeading.current?.focus();
      focusEntry.current = false;
    }
  }, [restored, user]);

  useEffect(() => {
    if (user && groupsState?.user === user && focusGroup.current) {
      groupHeading.current?.focus();
      if (groupHeading.current) focusGroup.current = false;
    }
  }, [user, groupsState, groupId]);

  function chooseUser(name: string) {
    try {
      sessionStorage.setItem(PROFILE_KEY, name);
      setProfileError("");
      focusGroup.current = true;
      setUser(name);
    } catch {
      setProfileError(
        "เบราว์เซอร์จำผู้ใช้ไม่ได้ กรุณาตรวจการตั้งค่าการเก็บข้อมูลแล้วเลือกชื่ออีกครั้ง",
      );
    }
  }

  const exitProfile = useCallback(() => {
    if (mutationBusyRef.current) return;
    try {
      sessionStorage.removeItem(PROFILE_KEY);
    } catch {
      setProfileError(
        "เบราว์เซอร์ล้างผู้ใช้เดิมไม่ได้ กรุณาตรวจการตั้งค่าการเก็บข้อมูลแล้วลองอีกครั้ง",
      );
      return;
    }
    focusEntry.current = true;
    setUser(null);
    setGroupId(null);
    setGroupsState(null);
    setGroupsError("");
    setProfileError("");
  }, []);

  const groups = groupsState?.user === user ? groupsState.groups : null;

  function navigate(
    next: () => void,
    destination: "profile" | "group",
    trigger: HTMLElement,
  ) {
    if (pending || mutationBusyRef.current) return;
    if (exitGuardRef.current) exitGuardRef.current(next, destination, trigger);
    else next();
  }

  function chooseGroup(id: number | null) {
    focusGroup.current = true;
    setGroupId(id);
  }
  function updatePending(value: PendingExpense | null) {
    if (value) sessionStorage.setItem(PENDING_KEY, JSON.stringify(value));
    else {
      try {
        if (user) sessionStorage.setItem(PROFILE_KEY, user);
      } catch {
        setProfileError(
          "เบราว์เซอร์จำผู้ใช้ไม่ได้ กรุณาตรวจการตั้งค่าการเก็บข้อมูลแล้วลองส่งรายการเดิมอีกครั้ง",
        );
        return false;
      }
      try {
        sessionStorage.removeItem(PENDING_KEY);
      } catch {
        /* Replaying a retained key remains safe. */
      }
    }
    setProfileError("");
    setPending(value);
    return true;
  }

  return (
    <>
      <a className="skip-link" href="#workspace">
        ข้ามไปเนื้อหา
      </a>
      <header className="topbar">
        <a
          href="#workspace"
          className="brand"
          aria-label="SplitBill หน้าหลัก"
          aria-disabled={pending || working ? true : undefined}
          onClick={(event) => {
            if (pending || mutationBusyRef.current) {
              event.preventDefault();
              return;
            }
            if (user && groupId !== null && groups && groups.length > 1) {
              event.preventDefault();
              navigate(() => chooseGroup(null), "group", event.currentTarget);
            }
          }}
        >
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
        {user && (
          <div className="profile-control">
            <span
              className="profile-identity"
              aria-label={`ผู้ใช้ปัจจุบัน ${user}`}
            >
              <span className="avatar" aria-hidden="true">
                {user[0].toUpperCase()}
              </span>
              <span>{user}</span>
            </span>
            <button
              id="change-user"
              className="button secondary compact"
              disabled={!!pending || working}
              title={
                pending
                  ? "ยืนยันบิลเดิมก่อนเปลี่ยนผู้ใช้"
                  : working
                    ? "รอให้ทำรายการเสร็จก่อนเปลี่ยนผู้ใช้"
                    : undefined
              }
              onClick={(event) =>
                navigate(exitProfile, "profile", event.currentTarget)
              }
            >
              เปลี่ยนผู้ใช้
            </button>
          </div>
        )}
      </header>
      <main
        id="workspace"
        className={`page-shell${user === null ? " entry-shell" : groupId === null ? " groups-shell" : ""}`}
      >
        {profileError && (
          <div className="notice error" role="alert">
            {profileError}
          </div>
        )}
        {!restored ? (
          <Loading />
        ) : user === null ? (
          <section className="profile-entry" aria-labelledby="entry-heading">
            <h1 id="entry-heading" ref={entryHeading} tabIndex={-1}>
              คุณคือใคร?
            </h1>
            <p className="entry-description">
              เลือกชื่อเพื่อดูกลุ่มและเริ่มแบ่งบิล
            </p>
            <div className="profile-list">
              {USERS.map((name) => (
                <button
                  className="profile-choice"
                  key={name}
                  onClick={() => chooseUser(name)}
                >
                  <span className="avatar" aria-hidden="true">
                    {name[0].toUpperCase()}
                  </span>
                  <span>{name}</span>
                  <Chevron />
                </button>
              ))}
            </div>
            <p className="entry-note">เลือกจากผู้ใช้ตัวอย่างของแอป</p>
          </section>
        ) : (
          <>
            {groupId !== null && groups && groups.length > 1 && (
              <button
                className="group-home-link"
                disabled={!!pending || working}
                onClick={(event) =>
                  navigate(
                    () => chooseGroup(null),
                    "group",
                    event.currentTarget,
                  )
                }
              >
                <Chevron /> กลับไปกลุ่มของฉัน
              </button>
            )}
            {groupId !== null ? (
              <div className="group-heading">
                <div>
                  <p className="context-label">ค่าใช้จ่ายของกลุ่ม</p>
                  <h1 ref={groupHeading} tabIndex={-1}>
                    {groups?.find((group) => group.id === groupId)?.name ??
                      (groups ? "เลือกกลุ่มของคุณ" : "มาแบ่งบิลกัน")}
                  </h1>
                </div>
                <label className="group-control">
                  <span>กลุ่ม</span>
                  <select
                    aria-label="กลุ่ม"
                    value={groupId ?? ""}
                    disabled={!groups || !!pending || working}
                    onChange={(event) => {
                      const id = Number(event.target.value);
                      if (id !== groupId)
                        navigate(
                          () => chooseGroup(id),
                          "group",
                          event.currentTarget,
                        );
                    }}
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
            ) : (
              <div className="groups-intro">
                <h1 ref={groupHeading} tabIndex={-1}>
                  กลุ่มของฉัน
                </h1>
                <p>เลือกกลุ่มเพื่อดูค่าใช้จ่ายและเริ่มแบ่งบิล</p>
              </div>
            )}
            {storageError && (
              <div className="notice error" role="alert">
                <p>{storageError}</p>
                {!pending && (
                  <button
                    className="button secondary"
                    onClick={() => {
                      if (pending) return;
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
                )}
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
            {groups && groups.length > 1 && groupId === null && (
              <section className="groups-home" aria-label="เลือกกลุ่ม">
                <p className="groups-count">{groups.length} กลุ่ม</p>
                <ul className="group-choices">
                  {groups.map((group) => (
                    <li key={group.id}>
                      <button
                        className="profile-choice group-choice"
                        onClick={() => chooseGroup(group.id)}
                      >
                        <span>{group.name}</span>
                        <Chevron />
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
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
                busyRef={mutationBusyRef}
                exitGuardRef={exitGuardRef}
                onWorkingChange={setWorking}
              />
            )}
          </>
        )}
      </main>
      <footer className="page-footer">
        <span>SplitBill</span>
        <span>เห็นส่วนแบ่งชัด ครบทุกสตางค์</span>
      </footer>
    </>
  );
}

function Chevron() {
  return (
    <svg
      aria-hidden="true"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m9 5 7 7-7 7" />
    </svg>
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
  busyRef,
  exitGuardRef,
  onWorkingChange,
}: {
  user: string;
  groupId: number;
  pending: PendingExpense | null;
  updatePending: (value: PendingExpense | null) => boolean;
  storageError: boolean;
  busyRef: RefObject<boolean>;
  exitGuardRef: RefObject<LeaveGuard | null>;
  onWorkingChange: (working: boolean) => void;
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
  const form = useRef<ExpenseFormHandle>(null);
  const [destination, setDestination] = useState<"profile" | "group" | null>(
    null,
  );
  const confirmExit = destination !== null;
  const nextActionRef = useRef<(() => void) | null>(null);
  const navigationTriggerRef = useRef<HTMLElement | null>(null);
  const exitCancel = useRef<HTMLButtonElement>(null);
  const loadSequence = useRef(0);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const deleteTrigger = useRef<HTMLButtonElement | null>(null);
  const path = `/groups/${groupId}`;

  useEffect(() => {
    const requestExit: LeaveGuard = (next, target, trigger) => {
      if (busyRef.current || pending) return;
      if (form.current?.isDirty) {
        setConfirmDelete(null);
        nextActionRef.current = next;
        navigationTriggerRef.current = trigger;
        setDestination(target);
        exitCancel.current?.focus();
      } else next();
    };
    exitGuardRef.current = requestExit;
    return () => {
      if (exitGuardRef.current === requestExit) exitGuardRef.current = null;
    };
  }, [busyRef, exitGuardRef, pending]);

  useEffect(() => {
    if (confirmExit) exitCancel.current?.focus();
  }, [destination, confirmExit]);

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
    onWorkingChange(true);
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
      if (!updatePending(null)) return false;
      setFormVersion((version) => version + 1);
      setNotice(
        expense.deleted
          ? "รายการเดิมถูกลบแล้ว จึงไม่นำกลับมาคิดยอด"
          : `บันทึก "${expense.description}" แล้ว`,
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
      busyRef.current = false;
      onWorkingChange(false);
    }
  }

  async function submit(body: ExpenseBody) {
    if (busyRef.current || pending) return false;
    busyRef.current = true;
    const intent = { key: crypto.randomUUID(), user, group: groupId, body };
    try {
      updatePending(intent);
    } catch {
      setActionError(
        "เบราว์เซอร์เก็บรายการรอส่งไม่ได้ จึงยังไม่ได้ส่งบิล กรุณาตรวจการตั้งค่าการเก็บข้อมูลแล้วลองอีกครั้ง",
      );
      busyRef.current = false;
      return false;
    }
    return send(intent);
  }

  return (
    <>
      {confirmExit && (
        <section
          className="profile-exit-confirm"
          aria-labelledby="exit-heading"
        >
          <h2 id="exit-heading">มีร่างบิลที่ยังไม่ได้บันทึก</h2>
          <p>
            ถ้าเปลี่ยน{destination === "profile" ? "ผู้ใช้" : "กลุ่ม"}{" "}
            ข้อมูลที่กรอกไว้ในบิลนี้จะถูกล้าง
          </p>
          <div className="exit-actions">
            <button
              className="button secondary"
              ref={exitCancel}
              onClick={() => {
                nextActionRef.current = null;
                setDestination(null);
                if (navigationTriggerRef.current?.isConnected)
                  navigationTriggerRef.current.focus();
              }}
            >
              กลับไปแก้บิล
            </button>
            <button
              className="button destructive"
              disabled={saving || deleting !== null || !!pending}
              onClick={() => {
                if (!busyRef.current && !pending) nextActionRef.current?.();
              }}
            >
              ทิ้งร่างและเปลี่ยน{destination === "profile" ? "ผู้ใช้" : "กลุ่ม"}
            </button>
          </div>
        </section>
      )}
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
              &quot;{pending.body.description}&quot; ·{" "}
              {formatMoney(pending.body.amount)} บาท · {pending.user}
            </p>
            <p>
              ถ้าการเชื่อมต่อขัดข้อง ให้ส่งรายการเดิมอีกครั้งก่อนเริ่มบิลใหม่
              หรือเปลี่ยนผู้ใช้ ระบบจะตรวจรายการซ้ำให้
            </p>
          </div>
          <button
            className="button primary"
            disabled={saving}
            onClick={() => {
              if (busyRef.current) return;
              busyRef.current = true;
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
              ? "บันทึกการเปลี่ยนแปลงแล้ว แต่ยังโหลดข้อมูลล่าสุดไม่ได้: "
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
              ref={form}
              key={formVersion}
              group={snapshot.group}
              user={user}
              disabled={
                !!pending ||
                saving ||
                deleting !== null ||
                storageError ||
                confirmExit
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
                  <p>เงินที่จ่ายไป ลบส่วนแบ่งของตัวเอง</p>
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
                  ยอดนี้เป็นยอดสุทธิ ยังไม่ระบุว่าใครต้องโอนให้ใคร
                </p>
              </div>
              <div className="group-members">
                <h3>สมาชิกในกลุ่ม</h3>
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
                <h3>ยังไม่มีรายการค่าใช้จ่าย</h3>
                <p>
                  เพิ่มค่าใช้จ่ายที่ออกให้เพื่อน เช่น ค่าอาหารหรือค่ารถ
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
                          disabled={
                            !!pending || deleting !== null || confirmExit
                          }
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
                          ลบ &quot;{expense.description}&quot;
                          ออกจากรายการและยอดสุทธิ?
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
                              if (busyRef.current) return;
                              busyRef.current = true;
                              onWorkingChange(true);
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
                                setNotice(`ลบ "${expense.description}" แล้ว`);
                                await refresh();
                                if (heading?.isConnected) heading.focus();
                              } catch (error) {
                                setActionError(errorMessage(error));
                              } finally {
                                busyRef.current = false;
                                onWorkingChange(false);
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

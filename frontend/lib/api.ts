export type Group = { id: number; name: string };
export type GroupDetail = Group & { members: string[] };
export type Expense = {
  id: number;
  group_id: number;
  description: string;
  paid_by: string;
  amount: string;
  split_type: "equal" | "exact";
  shares: Record<string, string>;
  created_at: string;
  deleted: boolean;
};
export type ExpenseBody = {
  description: string;
  paid_by: string;
  amount: string;
  split:
    | { type: "equal"; members: string[] }
    | { type: "exact"; shares: Record<string, string> };
};
export type PendingExpense = {
  key: string;
  user: string;
  group: number;
  body: ExpenseBody;
};
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

const messages: Record<string, string> = {
  unauthenticated: "ไม่พบผู้ใช้นี้ กรุณาเลือกผู้ใช้อีกครั้ง",
  group_not_found:
    "ไม่พบกลุ่มนี้ หรือคุณไม่มีสิทธิ์เข้าถึง กรุณาเลือกกลุ่มใหม่",
  expense_not_found: "ไม่พบรายการนี้ ลองโหลดรายการล่าสุดอีกครั้ง",
  expense_delete_forbidden: "เฉพาะคนที่จ่ายเงินเท่านั้นที่ลบรายการนี้ได้",
  invalid_amount:
    "ระบุจำนวนเงินมากกว่า 0 ไม่เกิน 9,999,999,999.99 บาท และทศนิยมไม่เกิน 2 ตำแหน่ง",
  invalid_split: "ตรวจผู้ร่วมหารและยอดแบ่งให้รวมเท่ากับยอดบิล",
  invalid_payer: "ผู้จ่ายต้องเป็นสมาชิกของกลุ่มนี้",
  invalid_idempotency_key: "ส่งรายการไม่สำเร็จ กรุณาลองรายการเดิมอีกครั้ง",
  validation_error:
    "ข้อมูลยังไม่ครบหรือรูปแบบไม่ถูกต้อง กรุณาตรวจช่องกรอกอีกครั้ง",
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  user: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  const headers = new Headers(init.headers);
  headers.set("X-User", user);
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: init.signal
        ? AbortSignal.any([init.signal, AbortSignal.timeout(15000)])
        : AbortSignal.timeout(15000),
      headers,
      cache: "no-store",
    });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError(
      0,
      "ติดต่อระบบไม่ได้ กรุณาตรวจการเชื่อมต่อแล้วลองอีกครั้ง",
    );
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      messages[payload?.error?.code] ??
        "ระบบยังทำรายการไม่ได้ กรุณาลองอีกครั้ง",
    );
  }
  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      0,
      "ยังยืนยันผลจากระบบไม่ได้ กรุณาลองรายการเดิมอีกครั้ง",
    );
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "โหลดข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง";
}

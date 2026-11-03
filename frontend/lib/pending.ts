import type { PendingExpense } from "./api";
import { parseAmount } from "./money.ts";

export const PENDING_KEY = "splitbill.pending.v1";

export function decodePending(raw: string | null): PendingExpense | null {
  if (!raw || raw.length > 10000) return null;
  try {
    const value = JSON.parse(raw);
    const validUser = (user: unknown) =>
      typeof user === "string" &&
      ["alice", "bob", "carol", "dan"].includes(user);
    if (
      !value ||
      typeof value.key !== "string" ||
      !value.key ||
      value.key.length > 200 ||
      !validUser(value.user) ||
      !Number.isSafeInteger(value.group) ||
      value.group <= 0
    )
      return null;
    const body = value.body;
    if (
      !body ||
      typeof body.description !== "string" ||
      !body.description.trim() ||
      body.description.length > 500 ||
      !validUser(body.paid_by)
    )
      return null;
    const amount =
      typeof body.amount === "string" ? parseAmount(body.amount) : null;
    if (amount === null || amount <= 0n) return null;
    const split = body.split;
    if (split?.type === "equal") {
      if (
        !Array.isArray(split.members) ||
        !split.members.length ||
        !split.members.every(validUser) ||
        new Set(split.members).size !== split.members.length
      )
        return null;
    } else if (split?.type === "exact") {
      if (
        !split.shares ||
        Array.isArray(split.shares) ||
        typeof split.shares !== "object"
      )
        return null;
      const entries = Object.entries(split.shares);
      if (
        !entries.length ||
        !entries.every(
          ([member, share]) =>
            validUser(member) &&
            typeof share === "string" &&
            parseAmount(share) !== null,
        )
      )
        return null;
      if (
        entries.reduce(
          (sum, [, share]) => sum + parseAmount(share as string)!,
          0n,
        ) !== amount
      )
        return null;
    } else return null;
    return value as PendingExpense;
  } catch {
    return null;
  }
}

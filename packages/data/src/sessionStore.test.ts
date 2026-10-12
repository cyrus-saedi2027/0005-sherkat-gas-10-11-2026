import { ANONYMOUS, can, canAny, createSessionStore, LOADING, type SessionSubject } from "./sessionStore";

describe("createSessionStore", () => {
  it("starts loading and moves between states", () => {
    const s = createSessionStore();
    expect(s.getState()).toBe(LOADING);
    const subject: SessionSubject = { type: "user", id: 7 };
    s.setSession(subject);
    expect(s.getState()).toEqual({ status: "authenticated", subject });
    s.setLoading();
    expect(s.getState()).toEqual({ status: "loading", subject });
    s.clearSession();
    expect(s.getState()).toBe(ANONYMOUS);
  });

  it("notifies subscribers only on real changes, with a stable snapshot otherwise", () => {
    const s = createSessionStore(ANONYMOUS);
    const listener = vi.fn();
    const off = s.subscribe(listener);
    const before = s.getState();
    s.clearSession(); // already anonymous
    expect(listener).not.toHaveBeenCalled();
    expect(s.getState()).toBe(before);
    s.setSession({ type: "staff", id: 1 });
    expect(listener).toHaveBeenCalledTimes(1);
    off();
    s.clearSession();
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("can be cleared from outside React (ApiClient onSessionExpired)", () => {
    const s = createSessionStore();
    const onSessionExpired = () => s.clearSession();
    s.setSession({ type: "user", id: 3 });
    onSessionExpired();
    expect(s.getState().status).toBe("anonymous");
  });
});

describe("can / canAny", () => {
  const operator: SessionSubject = {
    type: "staff",
    id: 2,
    roles: ["operator"],
    permissions: ["readings.view", "readings.review", "settings.view"],
  };
  const admin: SessionSubject = { type: "staff", id: 1, roles: ["super_admin"], permissions: [] };
  const user: SessionSubject = { type: "user", id: 9, permissions: ["readings.review"] };

  it("checks staff permissions", () => {
    expect(can(operator, "readings.review")).toBe(true);
    expect(can(operator, "settings.finance_edit")).toBe(false);
    expect(can(operator, "data.delete")).toBe(false);
  });

  it("gives super_admin everything", () => {
    expect(can(admin, "data.delete")).toBe(true);
    expect(can(admin, "settings.finance_edit")).toBe(true);
  });

  it("never grants permissions to subscribers or nobody", () => {
    expect(can(user, "readings.review")).toBe(false);
    expect(can(null, "dashboard.view")).toBe(false);
    expect(can({ type: "staff", id: 4 }, "dashboard.view")).toBe(false);
  });

  it("canAny", () => {
    expect(canAny(operator, ["settings.edit", "settings.view"])).toBe(true);
    expect(canAny(operator, ["settings.edit", "staff.manage"])).toBe(false);
    expect(canAny(operator, [])).toBe(false);
  });
});

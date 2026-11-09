import { onMounted, onUnmounted, ref } from "vue";
import { api, refresh, advanceSession, type User } from "../api";

/** Authentication lifecycle is independent of the portal's presentation. */
export function useSession() {
  const user = ref<User | null>(null),
    demo = ref(false),
    setup = ref(false),
    ready = ref(false),
    busy = ref(false),
    error = ref(""),
    username = ref(""),
    password = ref("");
  async function initialize() {
    try {
      const status = await api<{
        setup_required: boolean;
        demo_mode?: boolean;
      }>("auth/status");
      setup.value = status.setup_required;
      demo.value = status.demo_mode === true;
      if (!setup.value) {
        try {
          user.value = await api<User>("auth/me");
        } catch {
          /* Login is shown when there is no active session. */
        }
      }
    } catch (e) {
      error.value = (e as Error).message;
    } finally {
      ready.value = true;
    }
  }
  async function signIn() {
    busy.value = true;
    error.value = "";
    advanceSession();
    try {
      user.value = await api<User>(
        "auth/" + (setup.value ? "setup" : "login"),
        "POST",
        { username: username.value, password: password.value },
      );
      setup.value = false;
      password.value = "";
      refresh();
    } catch (e) {
      error.value = (e as Error).message;
    } finally {
      busy.value = false;
    }
  }
  async function logout() {
    advanceSession();
    try {
      await api("auth/logout", "POST");
      user.value = null;
      password.value = "";
      return true;
    } catch (e) {
      error.value = (e as Error).message;
      return false;
    }
  }
  function expired() {
    advanceSession();
    user.value = null;
    password.value = "";
    error.value = "Sua sessão expirou. Entre novamente.";
  }
  onMounted(() => {
    initialize();
    window.addEventListener("campusops:expired", expired);
  });
  onUnmounted(() => window.removeEventListener("campusops:expired", expired));
  return {
    demo,
    user,
    setup,
    ready,
    busy,
    error,
    username,
    password,
    signIn,
    logout,
  };
}

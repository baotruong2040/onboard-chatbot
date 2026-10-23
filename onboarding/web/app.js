"use strict";
const log = document.querySelector("#messages");
const input = document.querySelector("#message");
const status = document.querySelector("#status");
const send = document.querySelector("#send");
const fresh = document.querySelector("#new");
let conversation = null;
let busy = false;
const storageKey = "onboarding.conversation_id";

function lock(value) {
  busy = value;
  send.disabled = value;
  fresh.disabled = value;
  input.disabled = value;
}
function bubble(role, text) {
  const item = document.createElement("article");
  item.className = "message " + (role === "user" ? "user" : "assistant");
  const label = document.createElement("strong");
  label.textContent = role === "user" ? "Bạn" : "Trợ lý";
  const content = document.createElement("p");
  content.textContent = text;
  item.append(label, content);
  log.append(item);
  log.scrollTop = log.scrollHeight;
}
async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(typeof data.detail === "string" ? data.detail : "Yêu cầu chưa hợp lệ.");
    error.status = response.status;
    throw error;
  }
  return data;
}
function remember(id) {
  conversation = id;
  try { localStorage.setItem(storageKey, id); } catch (_) { /* Chat still works without persistence. */ }
}
async function createConversation() {
  const data = await api("/api/conversations", {method: "POST"});
  remember(data.conversation_id);
  log.replaceChildren();
}
async function initialize() {
  lock(true);
  status.textContent = "Đang tải cuộc trò chuyện…";
  try {
    let saved;
    try { saved = localStorage.getItem(storageKey); } catch (_) {}
    if (saved) {
      try {
        const data = await api(`/api/conversations/${encodeURIComponent(saved)}/messages`);
        remember(data.conversation_id);
        log.replaceChildren();
        data.messages.forEach(message => bubble(message.role, message.content));
      } catch (error) {
        if (error.status !== 404) throw error;
        await createConversation();
      }
    } else await createConversation();
    status.textContent = "";
  } catch (_) { status.textContent = "Không tải được cuộc trò chuyện. Thử tải lại trang hoặc chọn Cuộc trò chuyện mới."; }
  finally { lock(false); }
}
fresh.addEventListener("click", async () => {
  if (busy) return;
  lock(true);
  try { await createConversation(); input.value = ""; status.textContent = ""; }
  catch (_) { status.textContent = "Chưa tạo được cuộc trò chuyện. Hãy thử lại."; }
  finally { lock(false); input.focus(); }
});
document.querySelector("#form").addEventListener("submit", async event => {
  event.preventDefault();
  if (busy || !input.value.trim()) return;
  const question = input.value;
  lock(true);
  status.textContent = "Đang trả lời…";
  try {
    if (!conversation) await createConversation();
    const data = await api(`/api/conversations/${encodeURIComponent(conversation)}/messages`, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({message: question})
    });
    bubble("user", question);
    bubble("assistant", data.answer);
    input.value = "";
    status.textContent = "";
  } catch (error) {
    if (error.status === 404) {
      conversation = null;
      try { await createConversation(); } catch (_) {}
      status.textContent = "Phiên cũ không còn tồn tại. Hãy gửi lại câu hỏi trong phiên mới.";
    } else status.textContent = error instanceof TypeError ? "Không kết nối được backend. Hãy thử gửi lại." : error.message;
    input.value = question;
  } finally { lock(false); input.focus(); }
});
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    document.querySelector("#form").requestSubmit();
  }
});
initialize();

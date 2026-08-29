/**
 * Chat widget logic - used by chat.html. Talks to POST /api/v1/chat,
 * keeps a conversation_id across turns, and shows which layer answered
 * (database/FAQ vs RAG+AI vs "information unavailable") so users and
 * admins can see the pipeline is real, not a black box.
 */
(function () {
  const SOURCE_LABELS = {
    faq: "Verified FAQ answer",
    database: "Verified college record",
    rag_ollama: "AI-generated from approved college knowledge (Ollama)",
    rag_gemini: "AI-generated from approved college knowledge (Gemini fallback)",
    unavailable: "No verified information found",
  };

  let conversationId = null;
  let lastMessageId = null;

  function appendMessage(role, text, source) {
    const container = document.getElementById("chatMessages");
    const wrap = document.createElement("div");
    wrap.className = `rrase-msg ${role === "user" ? "rrase-msg-user" : "rrase-msg-bot"}`;
    wrap.textContent = text;
    container.appendChild(wrap);

    if (role === "assistant" && source) {
      const sourceLine = document.createElement("div");
      sourceLine.className = "rrase-msg-source";
      sourceLine.textContent = SOURCE_LABELS[source] || source;
      container.appendChild(sourceLine);
    }
    container.scrollTop = container.scrollHeight;
  }

  function appendTyping() {
    const container = document.getElementById("chatMessages");
    const el = document.createElement("div");
    el.className = "rrase-msg rrase-msg-bot";
    el.id = "rrase-typing";
    el.textContent = "Thinking...";
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  function removeTyping() {
    document.getElementById("rrase-typing")?.remove();
  }

  async function sendQuestion(question) {
    appendMessage("user", question);
    appendTyping();
    try {
      const data = await window.RraseAPI.request("/chat", {
        method: "POST",
        body: { question, conversation_id: conversationId },
        auth: window.RraseAPI.isLoggedIn(),
      });
      removeTyping();
      conversationId = data.conversation_id;
      lastMessageId = data.message.id;
      appendMessage("assistant", data.message.content, data.message.answer_source);
      document.getElementById("feedbackRow").classList.remove("d-none");
    } catch (err) {
      removeTyping();
      appendMessage("assistant", "Sorry, something went wrong reaching the assistant. Please try again.");
    }
  }

  async function sendFeedback(rating) {
    if (!lastMessageId) return;
    try {
      await window.RraseAPI.request("/feedback", {
        method: "POST",
        body: { message_id: lastMessageId, rating },
        auth: window.RraseAPI.isLoggedIn(),
      });
      document.getElementById("feedbackRow").classList.add("d-none");
    } catch (e) {
      /* non-critical */
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chatForm");
    const input = document.getElementById("chatInput");
    if (!form) return;

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const question = input.value.trim();
      if (!question) return;
      input.value = "";
      sendQuestion(question);
    });

    document.querySelectorAll(".rrase-suggested-chip").forEach((chip) => {
      chip.addEventListener("click", () => sendQuestion(chip.textContent.trim()));
    });

    document.getElementById("feedbackUp")?.addEventListener("click", () => sendFeedback(5));
    document.getElementById("feedbackDown")?.addEventListener("click", () => sendFeedback(1));

    appendMessage(
      "assistant",
      "Hi! I'm the RRASE College Assistant. Ask me about admissions, courses, departments, facilities, or notices."
    );
  });
})();

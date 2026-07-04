const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const imageInput = document.querySelector("#image-input");
const imageFilename = document.querySelector("#image-filename");
const imagePreview = document.querySelector("#image-preview");
const messages = document.querySelector("#messages");
const debugPanel = document.querySelector("#debug-panel");
const debugPrompt = document.querySelector("#debug-prompt");
const debugMessages = document.querySelector("#debug-messages");
const promptTokens = document.querySelector("#prompt-tokens");
const completionTokens = document.querySelector("#completion-tokens");
const totalTokens = document.querySelector("#total-tokens");
const finishReason = document.querySelector("#finish-reason");

function addMessage(sender, text, renderMarkdown = false) {
  const message = document.createElement("div");
  message.className = "message";

  const label = document.createElement("strong");
  label.className = "message-sender";
  label.textContent = `${sender}:`;

  const content = document.createElement("div");
  content.className = "message-content";

  if (renderMarkdown) {
    content.classList.add("markdown-content");
    content.innerHTML = DOMPurify.sanitize(marked.parse(text));
  } else {
    content.textContent = text;
  }

  message.append(label, content);
  messages.appendChild(message);
  return content;
}

function renderMarkdown(element, text) {
  element.innerHTML = DOMPurify.sanitize(marked.parse(text));
}

function displayValue(value) {
  return value ?? "N/A";
}

function formatDebugContent(content) {
  if (typeof content === "string") {
    return content;
  }

  return JSON.stringify(
    content,
    (key, value) => {
      if (key === "url" && String(value).startsWith("data:image/")) {
        return "[image data]";
      }
      return value;
    },
    2,
  );
}

function updateDebugView(data, prompt = data.prompt) {
  debugMessages.replaceChildren();
  debugPrompt.textContent = displayValue(prompt);

  for (const modelMessage of data.messages ?? []) {
    const container = document.createElement("div");
    container.className = "debug-message";

    const role = document.createElement("p");
    role.className = "debug-role";
    role.textContent = String(displayValue(modelMessage.role)).toUpperCase();

    const content = document.createElement("p");
    content.className = "debug-content";
    content.textContent = formatDebugContent(modelMessage.content);

    container.append(role, content);
    debugMessages.appendChild(container);
  }

  promptTokens.textContent = displayValue(data.usage?.prompt_tokens);
  completionTokens.textContent = displayValue(data.usage?.completion_tokens);
  totalTokens.textContent = displayValue(data.usage?.total_tokens);
  finishReason.textContent = displayValue(data.finish_reason);
  debugPanel.hidden = false;
}

async function readChatStream(response, assistantContent, prompt) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let reply = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    const events = buffer.split("\n\n");
    buffer = events.pop();

    for (const eventBlock of events) {
      const lines = eventBlock.split("\n");
      const eventName = lines
        .find((line) => line.startsWith("event:"))
        ?.slice(6)
        .trim();
      const dataText = lines
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");

      if (!dataText) {
        continue;
      }

      const data = JSON.parse(dataText);

      if (eventName === "chunk") {
        reply += data.content;
        renderMarkdown(assistantContent, reply);
      } else if (eventName === "done") {
        updateDebugView(data, prompt);
      } else if (eventName === "error") {
        throw new Error(data.message);
      }
    }

    if (done) {
      break;
    }
  }
}

imageInput.addEventListener("change", () => {
  const image = imageInput.files[0];

  if (!image) {
    imageFilename.textContent = "No image selected";
    imagePreview.removeAttribute("src");
    imagePreview.hidden = true;
    return;
  }

  imageFilename.textContent = `📷 ${image.name}`;
  imagePreview.src = URL.createObjectURL(image);
  imagePreview.hidden = false;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const userMessage = input.value.trim();

  if (!userMessage) {
    return;
  }

  addMessage("You", userMessage);
  input.value = "";

  try {
    const image = imageInput.files[0];

    if (image) {
      const formData = new FormData();
      formData.append("prompt", userMessage);
      formData.append("image", image);

      const response = await fetch("/chat/vision", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("The vision request failed.");
      }

      const data = await response.json();
      addMessage("Assistant", data.reply, true);
      updateDebugView(data, userMessage);
      return;
    }

    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: userMessage }),
    });

    if (!response.ok) {
      throw new Error("The request failed.");
    }

    const assistantContent = addMessage("Assistant", "", true);
    await readChatStream(response, assistantContent, userMessage);
  } catch (error) {
    addMessage("Error", "Could not connect to the backend.");
  }
});

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const imageInput = document.querySelector("#image-input");
const imageFilename = document.querySelector("#image-filename");
const imagePreview = document.querySelector("#image-preview");
const messages = document.querySelector("#messages");
const debugPanel = document.querySelector("#debug-panel");
const debugAssistant = document.querySelector("#debug-assistant");
const debugPrompt = document.querySelector("#debug-prompt");
const debugMessages = document.querySelector("#debug-messages");
const promptTokens = document.querySelector("#prompt-tokens");
const completionTokens = document.querySelector("#completion-tokens");
const totalTokens = document.querySelector("#total-tokens");
const finishReason = document.querySelector("#finish-reason");
const assistantForm = document.querySelector("#assistant-form");
const assistantName = document.querySelector("#assistant-name");
const systemPrompt = document.querySelector("#system-prompt");
const promptTemplate = document.querySelector("#prompt-template");
const assistantFormMessage = document.querySelector("#assistant-form-message");
const assistantList = document.querySelector("#assistant-list");
const selectedAssistantText = document.querySelector("#selected-assistant");
let selectedAssistant = null;

function updateSelectedAssistant() {
  selectedAssistantText.textContent = selectedAssistant
    ? `Selected assistant: ${selectedAssistant.name}`
    : "No assistant selected";
}

function renderAssistants(assistants) {
  assistantList.replaceChildren();
  const selectedId = selectedAssistant?.id;
  selectedAssistant =
    assistants.find((assistant) => assistant.id === selectedId) ?? null;
  updateSelectedAssistant();

  if (assistants.length === 0) {
    const emptyMessage = document.createElement("p");
    emptyMessage.textContent = "No assistants created yet.";
    assistantList.appendChild(emptyMessage);
    return;
  }

  for (const assistant of assistants) {
    const card = document.createElement("article");
    card.className = "assistant-card";
    if (assistant.id === selectedAssistant?.id) {
      card.classList.add("selected");
    }

    const name = document.createElement("h3");
    name.textContent = assistant.name;

    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.className = "select-assistant-button";
    selectButton.textContent =
      assistant.id === selectedAssistant?.id ? "Selected" : "Select assistant";
    selectButton.addEventListener("click", () => {
      selectedAssistant = assistant;
      renderAssistants(assistants);
    });

    const systemLabel = document.createElement("strong");
    systemLabel.textContent = "System prompt";
    const systemText = document.createElement("p");
    systemText.textContent = assistant.system_prompt;

    const templateLabel = document.createElement("strong");
    templateLabel.textContent = "Prompt template";
    const templateText = document.createElement("pre");
    templateText.textContent = assistant.prompt_template;

    const documentLabel = document.createElement("strong");
    documentLabel.textContent = "Context document";

    const documentStatus = document.createElement("p");
    documentStatus.className = "document-status";
    documentStatus.textContent = assistant.has_document
      ? `${assistant.document_filename} (${assistant.document_char_count} characters)`
      : "No document uploaded.";

    const uploadForm = document.createElement("form");
    uploadForm.className = "document-upload-form";

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".txt,text/plain";
    fileInput.required = true;
    fileInput.setAttribute("aria-label", `Text document for ${assistant.name}`);

    const uploadButton = document.createElement("button");
    uploadButton.type = "submit";
    uploadButton.textContent = assistant.has_document
      ? "Replace document"
      : "Upload document";

    uploadForm.append(fileInput, uploadButton);
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = fileInput.files[0];
      if (!file) {
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      uploadButton.disabled = true;
      documentStatus.textContent = "Uploading...";

      try {
        const response = await fetch(
          `/assistants/${encodeURIComponent(assistant.id)}/document`,
          {
            method: "POST",
            body: formData,
          },
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail ?? "Could not upload document.");
        }

        await loadAssistants();
      } catch (error) {
        documentStatus.textContent = error.message;
        uploadButton.disabled = false;
      }
    });

    card.append(
      name,
      selectButton,
      systemLabel,
      systemText,
      templateLabel,
      templateText,
      documentLabel,
      documentStatus,
      uploadForm,
    );
    assistantList.appendChild(card);
  }
}

async function loadAssistants() {
  try {
    const response = await fetch("/assistants");
    if (!response.ok) {
      throw new Error("Could not load assistants.");
    }
    renderAssistants(await response.json());
  } catch (error) {
    assistantList.textContent = error.message;
  }
}

assistantForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  assistantFormMessage.textContent = "";

  const template = promptTemplate.value.trim();
  if (!template.includes("{context}") || !template.includes("{user_input}")) {
    assistantFormMessage.textContent =
      "Prompt template must include {context} and {user_input}.";
    return;
  }

  try {
    const response = await fetch("/assistants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: assistantName.value,
        system_prompt: systemPrompt.value,
        prompt_template: template,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.[0]?.msg ?? error.detail ?? "Could not create assistant.");
    }

    assistantForm.reset();
    promptTemplate.value = "Context:\n{context}\n\nUser:\n{user_input}";
    assistantFormMessage.textContent = "Assistant created.";
    await loadAssistants();
  } catch (error) {
    assistantFormMessage.textContent = error.message;
  }
});

loadAssistants();

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
  debugAssistant.textContent = displayValue(data.assistant_name);
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
  const image = imageInput.files[0];

  if (!userMessage) {
    return;
  }

  if (!image && !selectedAssistant) {
    addMessage("Error", "Select an assistant before sending a text message.");
    return;
  }

  if (!image && !selectedAssistant.has_document) {
    addMessage("Error", "Upload a document for the selected assistant first.");
    return;
  }

  addMessage("You", userMessage);
  input.value = "";

  try {
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

    const response = await fetch("/assistants/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        assistant_id: selectedAssistant.id,
        message: userMessage,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? "The assistant request failed.");
    }

    const data = await response.json();
    addMessage(data.assistant_name, data.reply, true);
    updateDebugView(data, data.filled_prompt);
  } catch (error) {
    addMessage("Error", error.message);
  }
});

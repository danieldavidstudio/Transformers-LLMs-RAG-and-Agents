const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const imageInput = document.querySelector("#image-input");
const imageFilename = document.querySelector("#image-filename");
const imagePreview = document.querySelector("#image-preview");
const messages = document.querySelector("#messages");
const debugPanel = document.querySelector("#debug-panel");
const debugEmptyState = document.querySelector("#debug-empty-state");
const debugContent = document.querySelector("#debug-content");
const debugAssistant = document.querySelector("#debug-assistant");
const debugPrompt = document.querySelector("#debug-prompt");
const debugRetrievedChunks = document.querySelector("#debug-retrieved-chunks");
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
const chatEmptyState = document.querySelector("#chat-empty-state");
const chatAssistantSelect = document.querySelector("#chat-assistant-select");
const themeToggle = document.querySelector("#theme-toggle");
const tabButtons = document.querySelectorAll(".tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");
let selectedAssistant = null;
let assistantsCache = [];

function selectTab(tabId) {
  const tabExists = [...tabPanels].some((panel) => panel.id === tabId);
  const selectedTabId = tabExists ? tabId : "assistants-tab";

  for (const button of tabButtons) {
    const isSelected = button.dataset.tab === selectedTabId;
    button.setAttribute("aria-selected", String(isSelected));
    button.tabIndex = isSelected ? 0 : -1;
  }

  for (const panel of tabPanels) {
    panel.hidden = panel.id !== selectedTabId;
  }

  localStorage.setItem("easy-assistant-tab", selectedTabId);
}

for (const button of tabButtons) {
  button.addEventListener("click", () => selectTab(button.dataset.tab));
}

selectTab(localStorage.getItem("easy-assistant-tab") ?? "assistants-tab");

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.textContent = theme === "dark" ? "Light mode" : "Dark mode";
}

setTheme(localStorage.getItem("easy-assistant-theme") ?? "light");

themeToggle.addEventListener("click", () => {
  const newTheme =
    document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  setTheme(newTheme);
  localStorage.setItem("easy-assistant-theme", newTheme);
});

function updateSelectedAssistant() {
  selectedAssistantText.classList.toggle(
    "empty-state-banner",
    !selectedAssistant,
  );

  if (!selectedAssistant) {
    selectedAssistantText.textContent = "No assistant selected";
    chatEmptyState.textContent = "💬 Select an assistant to start chatting.";
    chatEmptyState.hidden = false;
  } else {
    selectedAssistantText.textContent =
      `Selected assistant: ${selectedAssistant.name}`;
    chatEmptyState.textContent =
      "📄 Upload a text document before asking questions.";
    chatEmptyState.hidden = selectedAssistant.has_document;
  }
}

function renderChatAssistantSelector(assistants) {
  chatAssistantSelect.replaceChildren();

  const emptyOption = document.createElement("option");
  emptyOption.value = "";
  emptyOption.textContent = "No assistant selected";
  chatAssistantSelect.appendChild(emptyOption);

  for (const assistant of assistants) {
    const option = document.createElement("option");
    option.value = assistant.id;
    option.textContent = assistant.name;
    chatAssistantSelect.appendChild(option);
  }

  chatAssistantSelect.value = selectedAssistant?.id ?? "";
}

chatAssistantSelect.addEventListener("change", () => {
  selectedAssistant =
    assistantsCache.find(
      (assistant) => assistant.id === chatAssistantSelect.value,
    ) ?? null;
  renderAssistants(assistantsCache);
});

function renderAssistants(assistants) {
  assistantsCache = assistants;
  assistantList.replaceChildren();
  const selectedId = selectedAssistant?.id;
  selectedAssistant =
    assistants.find((assistant) => assistant.id === selectedId) ?? null;
  updateSelectedAssistant();
  renderChatAssistantSelector(assistants);

  if (assistants.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state assistant-empty-state";

    const title = document.createElement("p");
    title.textContent = "🤖 No assistants created yet.";
    const description = document.createElement("p");
    description.textContent = "Create your first assistant to begin.";

    emptyState.append(title, description);
    assistantList.appendChild(emptyState);
    return;
  }

  for (const assistant of assistants) {
    const isSelected = assistant.id === selectedAssistant?.id;
    const card = document.createElement("article");
    card.className = "assistant-card";
    if (isSelected) {
      card.classList.add("selected");
    }

    const name = document.createElement("h3");
    name.textContent = `🤖 ${assistant.name}`;

    const badges = document.createElement("div");
    badges.className = "status-badges";

    if (isSelected) {
      const activeBadge = document.createElement("span");
      activeBadge.className = "status-badge active-badge";
      activeBadge.textContent = "Active";
      badges.appendChild(activeBadge);
    }

    const documentBadge = document.createElement("span");
    documentBadge.className = assistant.has_document
      ? "status-badge document-badge"
      : "status-badge empty-badge";
    documentBadge.textContent = assistant.has_document
      ? "📄 Has document"
      : "📄 No document";
    badges.appendChild(documentBadge);

    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.className = "select-assistant-button";
    selectButton.textContent = isSelected ? "Deselect" : "Select";
    selectButton.addEventListener("click", () => {
      selectedAssistant = isSelected ? null : assistant;
      renderAssistants(assistants);
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "delete-assistant-button";
    deleteButton.textContent = "🗑 Delete";
    deleteButton.addEventListener("click", async () => {
      const confirmed = window.confirm(
        `Delete "${assistant.name}" and its document?`,
      );
      if (!confirmed) {
        return;
      }

      deleteButton.disabled = true;
      try {
        const response = await fetch(
          `/assistants/${encodeURIComponent(assistant.id)}`,
          { method: "DELETE" },
        );
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail ?? "Could not delete assistant.");
        }

        if (selectedAssistant?.id === assistant.id) {
          selectedAssistant = null;
          updateSelectedAssistant();
        }
        await loadAssistants();
      } catch (error) {
        window.alert(error.message);
        deleteButton.disabled = false;
      }
    });

    const cardActions = document.createElement("div");
    cardActions.className = "card-actions";
    cardActions.append(selectButton, deleteButton);

    const systemText = document.createElement("p");
    systemText.textContent = assistant.system_prompt;
    const systemDetails = document.createElement("details");
    systemDetails.className = "prompt-details";
    const systemSummary = document.createElement("summary");
    systemSummary.textContent = "⚙ System prompt";
    systemDetails.append(systemSummary, systemText);

    const templateText = document.createElement("pre");
    templateText.textContent = assistant.prompt_template;
    const templateDetails = document.createElement("details");
    templateDetails.className = "prompt-details";
    const templateSummary = document.createElement("summary");
    templateSummary.textContent = "⚙ Prompt template";
    templateDetails.append(templateSummary, templateText);

    const documentStatus = document.createElement("p");
    documentStatus.className = "upload-status";

    const documentMetadata = document.createElement("dl");
    documentMetadata.className = "document-metadata";
    if (assistant.has_document) {
      const filenameRow = document.createElement("div");
      const filenameLabel = document.createElement("dt");
      filenameLabel.textContent = "File";
      const filenameValue = document.createElement("dd");
      filenameValue.textContent = assistant.document_filename;
      filenameRow.append(filenameLabel, filenameValue);

      const characterRow = document.createElement("div");
      const characterLabel = document.createElement("dt");
      characterLabel.textContent = "Characters";
      const characterValue = document.createElement("dd");
      characterValue.textContent = assistant.document_char_count;
      characterRow.append(characterLabel, characterValue);

      documentMetadata.append(filenameRow, characterRow);

      if (assistant.document_chunk_count != null) {
        const chunkRow = document.createElement("div");
        const chunkLabel = document.createElement("dt");
        chunkLabel.textContent = "Chunks";
        const chunkValue = document.createElement("dd");
        chunkValue.textContent = assistant.document_chunk_count;
        chunkRow.append(chunkLabel, chunkValue);
        documentMetadata.appendChild(chunkRow);
      }
    }

    const uploadForm = document.createElement("form");
    uploadForm.className = "document-upload-form";

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".txt,.md,text/plain,text/markdown";
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
      documentStatus.textContent = "Uploading and ingesting...";

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
      badges,
      cardActions,
      documentMetadata,
      systemDetails,
      templateDetails,
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
    promptTemplate.value = `Use only the information in the context below to answer the question.

If the answer is not contained in the context, say:
"I don't know based on the provided document."

Context
----------------
{context}
----------------

Question:
{user_input}`;
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

  let icon = "🤖";
  if (sender === "You") {
    message.classList.add("user-message");
    icon = "🙂";
  } else if (sender === "Error") {
    message.classList.add("error-message");
    icon = "⚠️";
  } else {
    message.classList.add("assistant-message");
  }

  const label = document.createElement("strong");
  label.className = "message-sender";
  label.textContent = `${icon} ${sender}`;

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
  debugEmptyState.hidden = true;
  debugContent.hidden = false;
  debugMessages.replaceChildren();
  debugRetrievedChunks.replaceChildren();
  debugAssistant.textContent = displayValue(data.assistant_name);
  debugPrompt.textContent = displayValue(prompt);

  const retrievedChunks = data.retrieved_chunks ?? [];
  if (retrievedChunks.length === 0) {
    const emptyChunks = document.createElement("p");
    emptyChunks.className = "debug-empty-note";
    emptyChunks.textContent = "No retrieved chunks for this request.";
    debugRetrievedChunks.appendChild(emptyChunks);
  }

  for (const chunk of retrievedChunks) {
    const container = document.createElement("article");
    container.className = "debug-chunk";

    const heading = document.createElement("p");
    heading.className = "debug-chunk-heading";
    heading.textContent =
      `${chunk.id} · similarity ${displayValue(chunk.similarity)}`;

    const text = document.createElement("p");
    text.className = "debug-content";
    text.textContent = chunk.text ?? chunk.preview ?? "";

    container.append(heading, text);
    debugRetrievedChunks.appendChild(container);
  }

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

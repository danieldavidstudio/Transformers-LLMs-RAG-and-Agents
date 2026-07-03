const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");

function addMessage(sender, text) {
  const message = document.createElement("p");
  message.className = "message";
  message.textContent = `${sender}: ${text}`;
  messages.appendChild(message);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const userMessage = input.value.trim();

  if (!userMessage) {
    return;
  }

  addMessage("You", userMessage);
  input.value = "";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: userMessage }),
    });

    if (!response.ok) {
      throw new Error("The request failed.");
    }

    const data = await response.json();
    addMessage("Assistant", data.reply);
  } catch (error) {
    addMessage("Error", "Could not connect to the backend.");
  }
});

let reading = false;
let currentQuestion = null;

// Function to safely create menu
function createReadMenu() {
  // Remove any existing menus first
  browser.contextMenus.remove("readText").catch(() => {});
  browser.contextMenus.remove("explainText").catch(() => {});
  browser.contextMenus.remove("summarizeText").catch(() => {});
  browser.contextMenus.remove("answerQuestion").catch(() => {});
  browser.contextMenus.remove("stopReading").catch(() => {});

  // Create new menus
  browser.contextMenus.create({
    id: "readText",
    title: "Read Text Directly",
    contexts: ["selection"]
  });

  browser.contextMenus.create({
    id: "explainText",
    title: "Explain & Read with AI",
    contexts: ["selection"]
  });

  browser.contextMenus.create({
    id: "summarizeText",
    title: "Summarize & Read with AI",
    contexts: ["selection"]
  });

  browser.contextMenus.create({
    id: "answerQuestion",
    title: "Ask AI & Read Answer",
    contexts: ["selection"]
  });
}

// Create menus on script load
createReadMenu();
browser.runtime.onInstalled.addListener(createReadMenu);
browser.runtime.onStartup.addListener(createReadMenu);

// Function to read text directly
async function readTextDirectly(text) {
  try {
    await fetch("http://127.0.0.1:8000/read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text })
    });
    return true;
  } catch (error) {
    console.error("Read failed:", error);
    return false;
  }
}

// Function to explain and read text using Groq
async function explainAndReadText(text) {
  try {
    await fetch("http://127.0.0.1:8000/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text })
    });
    return true;
  } catch (error) {
    console.error("Explain failed:", error);
    return false;
  }
}

// Function to summarize and read text using Groq
async function summarizeAndReadText(text) {
  try {
    await fetch("http://127.0.0.1:8000/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text, length: "medium" })
    });
    return true;
  } catch (error) {
    console.error("Summarize failed:", error);
    return false;
  }
}

// Function to answer question using Groq
async function answerQuestion(questionText) {
  try {
    await fetch("http://127.0.0.1:8000/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: questionText })
    });
    return true;
  } catch (error) {
    console.error("Answer failed:", error);
    return false;
  }
}

// Main click handler
browser.contextMenus.onClicked.addListener(async (info, tab) => {
  // Stop reading
  if (info.menuItemId === "stopReading") {
    await fetch("http://127.0.0.1:8000/stop", { method: "POST" });
    browser.contextMenus.remove("stopReading");
    reading = false;
    currentQuestion = null;
    return;
  }

  // Show stop button immediately
  if (!reading) {
    browser.contextMenus.create({
      id: "stopReading",
      title: "⏹ Stop Reading",
      contexts: ["all"]
    });
    reading = true;
  }

  // Read text directly
  if (info.menuItemId === "readText") {
    await readTextDirectly(info.selectionText);
  }

  // Explain & Read text
  if (info.menuItemId === "explainText") {
    await explainAndReadText(info.selectionText);
  }

  // Summarize & Read text
  if (info.menuItemId === "summarizeText") {
    await summarizeAndReadText(info.selectionText);
  }

  // Answer Question
  if (info.menuItemId === "answerQuestion") {
    await answerQuestion(info.selectionText);
  }
});
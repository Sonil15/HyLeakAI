const CDP = "http://127.0.0.1:9222";
const pageUrl = "https://sonil15.github.io/HyLeakAI/";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function connect() {
  const targets = await (await fetch(`${CDP}/json/list`)).json();
  const target = targets.find((item) => item.type === "page");
  if (!target) throw new Error("No browser page target found");
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  let id = 0;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      message.error ? reject(new Error(message.error.message)) : resolve(message.result);
    }
  });
  return {
    send(method, params = {}) {
      const requestId = ++id;
      socket.send(JSON.stringify({ id: requestId, method, params }));
      return new Promise((resolve, reject) => pending.set(requestId, { resolve, reject }));
    },
    close() { socket.close(); }
  };
}

async function main() {
  const cdp = await connect();
  try {
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Page.navigate", { url: pageUrl });
    for (let attempt = 0; attempt < 45; attempt += 1) {
      const result = await cdp.send("Runtime.evaluate", {
        expression: "document.readyState === 'complete' && Boolean(document.querySelector('#mode-seg'))",
        returnByValue: true
      });
      if (result.result.value) break;
      await sleep(1000);
    }
    await cdp.send("Runtime.evaluate", {
      expression: "document.querySelector('#mode-seg [data-mode=live]').click()"
    });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      const result = await cdp.send("Runtime.evaluate", {
        expression: "!document.querySelector('#live-simulation').disabled && !document.querySelector('#run-live').disabled",
        returnByValue: true
      });
      if (result.result.value) { ready = true; break; }
      await sleep(1000);
    }
    if (!ready) throw new Error("Live controls never became ready");
    await cdp.send("Runtime.evaluate", {
      expression: "document.querySelector('#live-fault-count').value = 3; document.querySelector('#run-live').click()"
    });
    let output;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const result = await cdp.send("Runtime.evaluate", {
        expression: `(() => ({
          status: document.querySelector('#live-status').textContent,
          mode: document.querySelector('#mode-copy').textContent,
          badge: document.querySelector('#live-badge').textContent,
          simulationDisabled: document.querySelector('#live-simulation').disabled,
          runDisabled: document.querySelector('#run-live').disabled,
          riskBadge: document.querySelector('#risk-source-badge').textContent,
          riskText: document.querySelector('#risk-readouts').textContent,
          faultRows: document.querySelectorAll('#waterfall .wf-row').length
        }))()`,
        returnByValue: true
      });
      output = result.result.value;
      if (output.status.includes("Live assessment complete")) break;
      if (output.status.includes("could not complete")) throw new Error(output.status);
      await sleep(1000);
    }
    if (!output.status.includes("Live assessment complete")) throw new Error("Assessment did not finish before timeout");
    console.log(JSON.stringify(output));
  } finally {
    cdp.close();
  }
}

main().catch((error) => { console.error(error.stack); process.exit(1); });

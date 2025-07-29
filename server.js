const express = require('express');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { connect, createDataItemSigner } = require('@permaweb/aoconnect');

const app = express();
const PORT = 3000;
const MAX_THROWS = 5;

const throwsPath = path.join(__dirname, 'throws.json');
const wallet = JSON.parse(fs.readFileSync('wallet.json', 'utf-8'));
const processId = 'hIoWDYQNWcOYt7x81SIy714-pqYPFhGeBOezf_rFMoU'; // your AO process ID

const ao = connect({
  MODE: "legacy",
  CU_URL: "https://cu.ao-testnet.xyz",
  MU_URL: "https://mu.ao-testnet.xyz",
  GATEWAY_URL: "https://arweave.net",
});

async function sendToAO(throwData) {
  const lua = `table.insert(throws, {
    id = "${throwData.id}",
    speed = ${throwData.speed},
    strength = ${throwData.strength},
    accel = ${throwData.accel}
  })`;

  const tags = [{ name: 'Action', value: 'Eval' }];
  const messageId = await ao.message({
    process: processId,
    data: lua,
    tags,
    signer: createDataItemSigner(wallet),
  });

  await new Promise(res => setTimeout(res, 100));
  const result = await ao.result({ process: processId, message: messageId });
  console.log(`✅ Sent throw ${throwData.id} to AO → ${messageId}`);
  return result;
}

// Serve frontend
app.use(express.static('public'));

// API: Start a throw
app.get('/start-throw', (req, res) => {
  exec('python3 throws.py', (err, stdout, stderr) => {
    if (err) {
      console.error('❌ Python Error:', err);
      return res.status(500).send('Failed to run throw script');
    }

    try {
      console.log("🧪 Raw Python output:", stdout);
      const cleaned = stdout.trim().split('\n').filter(Boolean).pop();
      const throwResult = JSON.parse(cleaned);
      console.log('📥 Throw result:', throwResult);

      // Read previous throws safely
      let allThrows = [];
      try {
        if (fs.existsSync(throwsPath)) {
          const raw = fs.readFileSync(throwsPath, 'utf-8');
          allThrows = raw.trim() ? JSON.parse(raw) : [];
        }
      } catch (e) {
        console.warn('⚠️ Failed to read or parse throws.json, resetting to []');
        allThrows = [];
      }

      // Save new throw, max 5
      allThrows.push(throwResult);
      if (allThrows.length > MAX_THROWS) {
        allThrows.shift();
      }

      fs.writeFileSync(throwsPath, JSON.stringify(allThrows, null, 2));
      res.json(throwResult);
    } catch (e) {
      console.error('❌ JSON parse error:', e);
      res.status(500).send('Failed to parse Python output');
    }
  });
});

// API: Get all throws
app.get('/throws', (req, res) => {
  try {
    if (fs.existsSync(throwsPath)) {
      const raw = fs.readFileSync(throwsPath, 'utf-8');
      const data = raw.trim() ? JSON.parse(raw) : [];
      res.json(data);
    } else {
      res.json([]);
    }
  } catch (e) {
    console.error('❌ Failed to read throws.json:', e);
    res.status(500).send('Error reading stored throws');
  }
});

// API: Upload all throws to AO
app.get('/upload-ao', async (req, res) => {
  try {
    if (!fs.existsSync(throwsPath)) return res.status(404).send('No throws to upload');

    const raw = fs.readFileSync(throwsPath, 'utf-8');
    const throwList = raw.trim() ? JSON.parse(raw) : [];

    for (const t of throwList) {
      await sendToAO(t);
    }

    fs.writeFileSync(throwsPath, '[]');
    res.send('✅ All throws uploaded to AO');
  } catch (err) {
    console.error('❌ Upload failed:', err);
    res.status(500).send('Upload to AO failed');
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});


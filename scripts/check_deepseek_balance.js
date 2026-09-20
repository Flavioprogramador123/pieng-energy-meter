const fs = require("fs");
const https = require("https");
const path = require("path");

const ENV_PATH = "C:\\Users\\flavi\\projeto\\pieng_postgres\\.env";

function readEnvKey(filePath, key) {
    const content = fs.readFileSync(filePath, "utf8");
    for (const line of content.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const idx = trimmed.indexOf("=");
        if (idx === -1) continue;
        const name = trimmed.slice(0, idx).trim();
        if (name === key) {
            return trimmed.slice(idx + 1).trim();
        }
    }
    return null;
}

let apiKey;
try {
    apiKey = readEnvKey(ENV_PATH, "DEEPSEEK_API_KEY");
} catch (err) {
    console.error(`Nao foi possivel ler ${ENV_PATH}: ${err.message}`);
    process.exit(1);
}

if (!apiKey) {
    console.error(`DEEPSEEK_API_KEY nao encontrada em ${ENV_PATH}`);
    process.exit(1);
}

const options = {
    hostname: "api.deepseek.com",
    path: "/user/balance",
    method: "GET",
    headers: {
        Authorization: `Bearer ${apiKey}`,
    },
};

const req = https.request(options, (res) => {
    let body = "";
    res.on("data", (chunk) => (body += chunk));
    res.on("end", () => {
        if (res.statusCode !== 200) {
            console.error(`Erro HTTP ${res.statusCode}: ${body}`);
            process.exitCode = 1;
            return;
        }
        const data = JSON.parse(body);
        if (!data.is_available) {
            console.log("Conta sem saldo disponivel para uso da API.");
        }
        for (const info of data.balance_infos || []) {
            console.log(`Moeda: ${info.currency}`);
            console.log(`  Saldo total:      ${parseFloat(info.total_balance).toFixed(2)}`);
            console.log(`  Credito gratis:   ${parseFloat(info.granted_balance).toFixed(2)}`);
            console.log(`  Saldo comprado:   ${parseFloat(info.topped_up_balance).toFixed(2)}`);
        }
    });
});

req.on("error", (err) => {
    console.error(`Erro de conexao: ${err.message}`);
    process.exitCode = 1;
});

req.end();

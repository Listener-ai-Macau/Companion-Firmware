#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const port = Number(process.argv[2] || 4185);
const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".png", "image/png"],
  [".pbm", "application/octet-stream"],
  [".json", "application/json; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"]
]);

const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent((request.url || "/").split("?")[0]);
  const target = path.resolve(root, `.${pathname}`);
  if (!target.startsWith(`${root}${path.sep}`)) {
    response.writeHead(403).end();
    return;
  }
  fs.stat(target, (statError, stat) => {
    if (statError || !stat.isFile()) {
      response.writeHead(404).end();
      return;
    }
    fs.readFile(target, (readError, data) => {
      if (readError) {
        response.writeHead(500).end();
        return;
      }
      response.writeHead(200, {
        "content-type": contentTypes.get(path.extname(target).toLowerCase()) || "application/octet-stream",
        "cache-control": "no-store"
      });
      response.end(data);
    });
  });
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`comp-req-616 browser server listening on http://127.0.0.1:${port}\n`);
});

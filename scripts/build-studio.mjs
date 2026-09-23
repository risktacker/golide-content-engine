import { cpSync, mkdirSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";

execFileSync(process.execPath, ["--check", "worker/index.js"], { stdio: "inherit" });
execFileSync(process.execPath, ["--check", "worker/social-oauth.js"], { stdio: "inherit" });
execFileSync(process.execPath, ["--check", "app/app.js"], { stdio: "inherit" });

rmSync("dist", { recursive: true, force: true });
mkdirSync("dist/client", { recursive: true });
mkdirSync("dist/server", { recursive: true });
cpSync("app", "dist/client", { recursive: true });
cpSync("worker/index.js", "dist/server/index.js");
cpSync("worker/social-oauth.js", "dist/server/social-oauth.js");

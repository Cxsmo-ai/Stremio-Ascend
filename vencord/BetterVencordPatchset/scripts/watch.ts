import { execFile, spawn } from "node:child_process";
import { existsSync, watch, copyFileSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { join, resolve as path_resolve } from "node:path";
import { promisify } from "node:util";

const args = process.argv.slice(2);
const isWebBuild = args.includes('--web') || args.includes('-w');
const isLegcordBuild = args.includes('--legcord') || args.includes('-l');

const SRC_DIR = path_resolve("./src/bdCompatLayer");
const DIST_DIR = path_resolve("./dist/Vencord/src/plugins/bdCompatLayer");
const BASE_DIR = path_resolve("./base/Vencord");

const fileDebounceTimers = new Map<string, NodeJS.Timeout>();

let isBuildInProgress = false;
let buildQueue: Array<() => void> = [];

const exec = promisify(execFile);

async function gitHash(dir: string) {
    const { stdout } = await exec("git", ["rev-parse", "--short", "HEAD"], { cwd: dir });
    return stdout.trim();
}

function debounceFile(filename: string, callback: () => void, delay: number = 100) {
    if (fileDebounceTimers.has(filename)) {
        clearTimeout(fileDebounceTimers.get(filename)!);
    }
    const timer = setTimeout(() => {
        callback();
        fileDebounceTimers.delete(filename);
    }, delay);
    fileDebounceTimers.set(filename, timer);
}

async function ensureDirectory(dir: string) {
    if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true });
    }
}

function copyDirectoryRecursive(src: string, dest: string) {
    if (!existsSync(src)) {
        console.log(`Source directory does not exist: ${src}`);
        return;
    }

    ensureDirectory(dest);

    const items = readdirSync(src);

    for (const item of items) {
        const srcPath = join(src, item);
        const destPath = join(dest, item);

        if (statSync(srcPath).isDirectory()) {
            copyDirectoryRecursive(srcPath, destPath);
        } else if (item.endsWith('.ts') || item.endsWith('.tsx') || item.endsWith('.js') || item.endsWith('.jsx') || item.endsWith('.css')) {
            copyFileSync(srcPath, destPath);
            console.log(`Copied: ${srcPath} -> ${destPath}`);
        }
    }
}

async function runPnpmDev() {
    return new Promise((resolve, reject) => {
        const child = spawn("pnpm", ["dev"], { // warning: untested
            cwd: DIST_DIR,
            stdio: "inherit",
            env: { ...process.env, VENCORD_HASH: process.env.VENCORD_HASH }
        });

        child.on("error", reject);
        child.on("close", (code) => {
            if (code === 0) resolve(null);
            else reject(new Error(`pnpm dev exited with code ${code}`));
        });
    });
}

async function runPnpmBuildWeb() {
    return new Promise((res, reject) => {
        const child = spawn("pnpm", ["buildWeb"], {
            cwd: path_resolve("./dist/Vencord"),
            stdio: "inherit",
            env: { ...process.env, VENCORD_HASH: process.env.VENCORD_HASH }
        });

        child.on("error", reject);
        child.on("close", (code) => {
            if (code === 0) res(null);
            else reject(new Error(`pnpm buildWeb exited with code ${code}`));
        });
    });
}

async function runLegcordBuildScript() {
    return new Promise((res, reject) => {
        const child = spawn("bash", ["util/copy-build-legcord.sh"], {
            cwd: path_resolve("."),
            stdio: "inherit",
        });

        child.on("error", reject);
        child.on("close", (code) => {
            if (code === 0) res(null);
            else reject(new Error(`Legcord copy script exited with code ${code}`));
        });
    });
}

async function processNextBuildInQueue() {
    if (buildQueue.length === 0) {
        isBuildInProgress = false;
        return;
    }

    const nextBuild = buildQueue.shift();
    if (nextBuild) {
        nextBuild();
    }
}

async function addToBuildQueue() {
    return new Promise<void>(resolve => {
        buildQueue.push(async () => {
            try {
                console.log("buildWeb exec");
                await runPnpmBuildWeb();
                if (isLegcordBuild) {
                    console.log("copy...");
                    await runLegcordBuildScript();
                    console.log("ok");
                }
                console.log("buildWeb done");
            } catch (error) {
                console.error("error during buildWeb:", error);
            } finally {
                processNextBuildInQueue();
            }
            resolve();
        });
        if (!isBuildInProgress) {
            isBuildInProgress = true;
            const buildToExecute = buildQueue.shift();
            if (buildToExecute) {
                buildToExecute();
            }
        }
    });
}

async function triggerWebBuild() {
    addToBuildQueue();
}

async function main() {
    if (isWebBuild || isLegcordBuild) {
        console.log("mode: Web build");
    } else {
        console.log("mode: Desktop build");
    }

    const builderHash = await gitHash(".");
    const baseHash = await gitHash(BASE_DIR);
    process.env.VENCORD_HASH = `${baseHash} (BetterVencord patchset built by ${builderHash})`;

    if (!existsSync(DIST_DIR)) {
        console.log("run regular build first");
        process.exit(1);
    }

    copyDirectoryRecursive(SRC_DIR, DIST_DIR);

    watch(SRC_DIR, { recursive: true }, (eventType, filename) => {
        if (filename && (filename.endsWith('.ts') || filename.endsWith('.tsx') || filename.endsWith('.js') || filename.endsWith('.jsx') || filename.endsWith('.css'))) {
            debounceFile(filename, () => {
                const srcPath = join(SRC_DIR, filename);
                const destPath = join(DIST_DIR, filename);
                process.env.VENCORD_HASH = `${baseHash} (BetterVencord patchset built by ${builderHash}, tainted at ${new Date().toISOString()})`;

                try {
                    ensureDirectory(join(DIST_DIR, filename).replace(/[^\/\\]*$/, ''));
                    copyFileSync(srcPath, destPath);
                    console.log(`updated: ${filename}`);

                    if (isWebBuild || isLegcordBuild) {
                        triggerWebBuild();
                    }
                } catch (err) {
                    console.error(`err during copy of ${filename}:`, err);
                }
            }, 100);
        }
    });

    if (isWebBuild || isLegcordBuild) {
        console.log("buildWeb init");
        await triggerWebBuild();
        console.log("startup done");
    } else {
        console.log("dev mode init");
        try {
            await runPnpmDev();
        } catch (error) {
            console.error("Error running pnpm dev:", error);
        }
    }
}

main().catch(console.error);

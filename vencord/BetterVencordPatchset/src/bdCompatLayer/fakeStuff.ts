/*
 * Vencord, a modification for Discord's desktop app
 * Copyright (c) 2022 Vendicated and contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

import { wreq } from "@webpack";
import { addLogger, compat_logger, evalInScope, findFirstLineWithoutX } from "./utils";

export const TARGET_HASH = "df5c2887eb5eddb8d9f3e470b51cdfa5cec814db";
export const TARGET_CONTEXT_MENU_NEW_HASH = "c10d0b67c0fd53fee582cf5b8bc4779e80006983";

export const FakeEventEmitter = class {
    callbacks: any;
    constructor() {
        this.callbacks = {};
    }

    on(event, cb) {
        if (!this.callbacks[event]) this.callbacks[event] = [];
        this.callbacks[event].push(cb);
    }

    off(event, cb) {
        const cbs = this.callbacks[event];
        if (cbs) {
            this.callbacks[event] = cbs.filter(callback => callback !== cb);
        }
    }

    emit(event, data) {
        const cbs = this.callbacks[event];
        if (cbs) {
            cbs.forEach(cb => cb(data));
        }
    }
};

export const addDiscordModules = async proxyUrl => {
    const context = {
        get WebpackModules() {
            return window.BdApi.Webpack;
        }
    };
    // const ModuleDataText = simpleGET(
    //     proxyUrl +
    //     `https://github.com/BetterDiscord/BetterDiscord/raw/${TARGET_HASH}/renderer/src/modules/discordmodules.js`
    // ).responseText.replaceAll("\r", "");
    const request = await fetchWithCorsProxyFallback(`https://github.com/BetterDiscord/BetterDiscord/raw/${TARGET_HASH}/renderer/src/modules/discordmodules.js`, undefined, proxyUrl);
    const ModuleDataText = (await request.text()).replaceAll("\r", "");
    const ev =
        "(" +
        (ModuleDataText.split("const DiscordModules = Utilities.memoizeObject(")[1]).split(/;\s*export default DiscordModules;/)[0];
    // const sourceBlob = new Blob([ev], { type: "application/javascript" });
    // const sourceBlobUrl = URL.createObjectURL(sourceBlob);
    // return { output: evalInScope(ev + "\n//# sourceURL=" + sourceBlobUrl, context), sourceBlobUrl };
    return { output: evalInScope(ev + "\n//# sourceURL=" + "betterDiscord://internal/DiscordModules.js", context), sourceBlobUrl: undefined };
};

function javascriptifyContextMenuModule(rawSourceCode: string) {
    let code = rawSourceCode;
    code = code.replace(/^\s*import\s+[^\n;]+;\s*/mg, '');
    code = code.replace(/export\s+default\s+ContextMenu\s*;/g, 'return ContextMenu;');

    code = code.replace(/\s+as\s+[A-Za-z0-9_$\.]+\b/g, '');

    code = code.replace(/([A-Za-z0-9_$\)\]\}])!(?=[\s;,\)\]\}])/g, '$1');

    code = code.replace(/\bmenuItemsId!/g, 'menuItemsId');

    code = code.replace(/(\.\.\.\s*[A-Za-z0-9_$]+)\s*:\s*any\[\]\s*/g, '$1');

    code = code.replace(/:\s*any\[\]/g, '');
    code = code.replace(/:\s*any\b/g, '');

    code = code.replace(/:\s*(any|object|string|boolean|number|Error|unknown|JSX\.Element)\b/g, '');

    code = code.replace(/([A-Za-z0-9_$\.\[\]'"]+)\s*\?\?=\s*([^;]+);/g, 'if ($1 == null) $1 = $2;');

    code = code.replace(/res\.props\.\s*children\?\.\s*props\.\s*navId/g,
        'res.props && res.props.children && res.props.children.props && res.props.children.props.navId');

    code = code.replace(/res\?\.\s*props\.\s*children\?\.\s*props\.\s*navId/g,
        'res.props && res.props.children && res.props.children.props && res.props.children.props.navId');

    code = code.replace(/typeof\s+res\?\.\s*type\s*===\s*("function"|'function')/g, 'res && typeof res.type === $1');

    code = code.replace(/res\?\.\s*props\.navId/g, 'res && res.props && res.props.navId');

    code = code.replace(/res\?\.\s*type/g, 'res && res.type');

    code = code.replace(/typeof\s+res\s*&&\s*res\.type\s*===\s*("function"|'function')/g, 'res && typeof res.type === $1');

    code = code.replace(/\/\/ eslint-disable-next-line react-hooks\/rules-of-hooks\s*/g, '');

    code = code.replace(/startupComplete\s*&&=\s*([^;]+);/g, 'startupComplete = startupComplete && ($1);');

    code = code.replace(/:\s*[A-Za-z0-9_$]+\[\]/g, '');

    code = code.trim() + '\n';

    const wrappedCode = `(function(Filters, getByKeys, getMangled, getModule, webpackRequire, Patcher, Logger, React) {
"use strict";
${code}
})`;
    return new Function(
        'Filters', 'getByKeys', 'getMangled', 'getModule', 'webpackRequire',
        'Patcher', 'Logger', 'React',
        `return ${wrappedCode}`
    );
}

export const addContextMenu = async (DiscordModules, proxyUrl) => {
    // /**
    //  * @type {string}
    //  */
    // const ModuleDataText = simpleGET(
    //     proxyUrl +
    //     `https://github.com/BetterDiscord/BetterDiscord/raw/${TARGET_HASH}/renderer/src/modules/api/contextmenu.js`
    // ).responseText.replaceAll("\r", "");
    const request = await fetchWithCorsProxyFallback(`https://github.com/BetterDiscord/BetterDiscord/raw/${TARGET_CONTEXT_MENU_NEW_HASH}/src/betterdiscord/api/contextmenu.ts`, undefined, proxyUrl);
    const ModuleDataText = (await request.text()).replaceAll("\r", "");
    /*
    const context = {
        get WebpackModules() {
            return window.BdApi.Webpack;
        },
        get Filters() {
            return window.BdApi.Webpack.Filters;
        },
        DiscordModules,
        get Patcher() {
            return window.BdApi.Patcher;
        }
    };
    const linesToRemove = findFirstLineWithoutX(
        ModuleDataText,
        "import"
    );
    // eslint-disable-next-line prefer-const
    let ModuleDataArr = ModuleDataText.split("\n");
    ModuleDataArr.splice(0, linesToRemove);
    ModuleDataArr.pop();
    ModuleDataArr.pop();
    // for (let i = 0; i < ModuleDataArr.length; i++) {
    //     const element = ModuleDataArr[i];
    //     if (element.trimStart().startsWith("Patcher.before(\"ContextMenuPatcher\", ")) {
    //         ModuleDataArr[i] = "debugger;" + element;
    //     }
    // }
    const ModuleDataAssembly =
        "(()=>{" +
        addLogger.toString() +
        ";const Logger = " + addLogger.name + "();const {React} = DiscordModules;" +
        ModuleDataArr.join("\n") +
        "\nreturn ContextMenu;})();";
    // const sourceBlob = new Blob([ModuleDataAssembly], {
    //     type: "application/javascript",
    // });
    // const sourceBlobUrl = URL.createObjectURL(sourceBlob);
    // const evaluatedContextMenu = evalInScope(ModuleDataAssembly + "\n//# sourceURL=" + sourceBlobUrl, context);
    const evaluatedContextMenu = evalInScope(ModuleDataAssembly + "\n//# sourceURL=" + "betterDiscord://internal/ContextMenu.js", context);
    // return { output: new evaluatedContextMenu(), sourceBlobUrl };
    return { output: new evaluatedContextMenu(), sourceBlobUrl: undefined };
    */
    const evaluatedContextMenu = javascriptifyContextMenuModule(ModuleDataText + "\n//# sourceURL=" + "betterDiscord://internal/ContextMenu.js")();
    return {
        output: new (evaluatedContextMenu(window.BdApi.Webpack.Filters, window.BdApi.Webpack.getByKeys, window.BdApi.Webpack.getMangled, window.BdApi.Webpack.getModule, wreq, window.BdApi.Patcher, window.BdApi.Logger, window.BdApi.React)),
        sourceBlobUrl: undefined,
    };
};

export async function fetchWithCorsProxyFallback(url: string, options: any = {}, corsProxy: string) {
    const reqId = (Date.now().toString(36) + Math.random().toString(36).slice(2, 6));
    try {
        compat_logger.debug(`[${reqId}] Requesting ${url}...`, options);
        const result = await fetch(url, options);
        compat_logger.debug(`[${reqId}] Success.`);
        return result;
    } catch (error) {
        if (options.method === undefined || options.method === "get") {
            compat_logger.debug(`[${reqId}] Failed, trying with proxy.`);
            try {
                const result = await fetch(`${corsProxy}${url}`, options);
                compat_logger.debug(`[${reqId}] (Proxy) Success.`);
                return result;
            } catch (error) {
                compat_logger.debug(`[${reqId}] (Proxy) Failed completely.`);
                throw error;
            }
        }
        compat_logger.debug(`[${reqId}] Failed completely.`);
        throw error;
    }
}

export { Patcher } from "./stuffFromBD";

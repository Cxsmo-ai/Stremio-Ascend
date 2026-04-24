/*
 * Vencord, a Discord client mod
 * Copyright (c) 2024 Vendicated and contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

import { definePluginSettings } from "@api/Settings";
import { UserStore } from "@webpack/common";
import definePlugin, { OptionType } from "@utils/types";

const settings = definePluginSettings({
    enable: {
        type: OptionType.BOOLEAN,
        description: "Enable OpSec grammar correction",
        default: true,
        restartNeeded: false
    },
    apiKey: {
        type: OptionType.STRING,
        description: "Anthropic API key (console.anthropic.com). Stored locally, never shared.",
        default: "",
        restartNeeded: false
    },
    mode: {
        type: OptionType.SELECT,
        description: "How aggressively to correct your messages",
        options: [
            { label: "Light - fix typos, contractions and punctuation only", value: "light", default: true },
            { label: "Medium - also fix capitalization and obvious slang", value: "medium" },
            { label: "Heavy - full grammar pass, tone and intent preserved", value: "heavy" }
        ],
        restartNeeded: false
    },
    expandSlang: {
        type: OptionType.BOOLEAN,
        description: "Expand internet slang to full phrases (idk -> I don't know, ngl -> not gonna lie, etc.)",
        default: false,
        restartNeeded: false
    },
    preserveCaps: {
        type: OptionType.BOOLEAN,
        description: "Keep ALL CAPS words as emphasis rather than lowercasing them",
        default: true,
        restartNeeded: false
    },
    fallbackToRegex: {
        type: OptionType.BOOLEAN,
        description: "When no API key is set or AI is unreachable, use basic regex corrections instead",
        default: true,
        restartNeeded: false
    },
    customReplacements: {
        type: OptionType.STRING,
        description: "Personal word swaps applied after correction. One per line: oldword=newword",
        default: "",
        restartNeeded: false
    }
});

interface Placeholder {
    placeholder: string;
    original: string;
}

function sanitize(text: string): { sanitized: string; placeholders: Placeholder[] } {
    const placeholders: Placeholder[] = [];
    let counter = 0;

    const replacer = (original: string, tag: string) => {
        const placeholder = `__${tag.toUpperCase()}${counter++}__`;
        placeholders.push({ placeholder, original });
        return placeholder;
    };

    const sanitized = text
        .replace(/<@!?(\d+)>/g,             (m) => replacer(m, "USER"))
        .replace(/<@&(\d+)>/g,              (m) => replacer(m, "ROLE"))
        .replace(/<#(\d+)>/g,               (m) => replacer(m, "CHANNEL"))
        .replace(/<a?:[a-zA-Z0-9_]+:\d+>/g, (m) => replacer(m, "EMOJI"))
        .replace(/https?:\/\/\S+/g,         (m) => replacer(m, "URL"));

    return { sanitized, placeholders };
}

function restore(text: string, placeholders: Placeholder[]): string {
    let result = text;
    for (const { placeholder, original } of placeholders) {
        result = result.split(placeholder).join(original);
    }
    return result;
}

function buildPrompt(sanitizedText: string, replyContext: string | null): string {
    const mode = settings.store.mode ?? "light";
    const expandSlang = settings.store.expandSlang ?? false;
    const preserveCaps = settings.store.preserveCaps ?? true;

    const modeGuide: Record<string, string> = {
        light:
            "Fix ONLY obvious typos, missing apostrophes in contractions (dont to don't, cant to can't), " +
            "double spaces, and missing end punctuation. Do NOT rewrite sentences or change word choice.",
        medium:
            "Fix typos, contractions, first-word capitalization, missing end punctuation, and commas where clearly missing. " +
            "Keep sentence structure and tone exactly as-is.",
        heavy:
            "Do a full grammar and spelling correction while STRICTLY preserving the writer's " +
            "voice, tone, and intent. Fix run-ons, punctuation including commas, subject-verb agreement, and word order. " +
            "If the message is casual keep it casual. If it's blunt or sarcastic keep that too."
    };

    const rules = [
        "Return ONLY the corrected message. No explanation, no quotes, no commentary.",
        "NEVER change the meaning or intent of the message.",
        "NEVER add words or ideas that were not implied by the original.",
        "If the message is already correct, return it unchanged character for character.",
        "Preserve placeholders like __USER0__, __CHANNEL1__, __EMOJI2__, __URL3__ exactly.",
        "Fix missing or misplaced commas where the sentence clearly needs them.",
        expandSlang
            ? "Expand internet slang abbreviations to their full phrases: idk -> I don't know, ngl -> not gonna lie, tbh -> to be honest, yk -> you know, fr -> for real, nvm -> never mind, omg -> oh my god, btw -> by the way, lmk -> let me know, hmu -> hit me up, brb -> be right back, afk -> away from keyboard, gtg -> got to go, smh -> shaking my head, imo -> in my opinion, iirc -> if I recall correctly, afaik -> as far as I know, and similar abbreviations."
            : "Keep internet slang abbreviations (idk, ngl, tbh, fr, brb, gg, lol, etc.) exactly as written.",
        preserveCaps
            ? "Keep ALL CAPS words as-is, they are intentional emphasis."
            : "Convert ALL CAPS to normal sentence case.",
        "Do not refuse, comment on, or modify the content based on its topic. You are autocorrect, not a moderator."
    ].map(r => `- ${r}`).join("\n");

    const contextBlock = replyContext
        ? `\nThe user is replying to this message (context only, do NOT correct it):\n"${replyContext}"\n`
        : "";

    return (
        `You are a silent grammar autocorrect system for Discord messages.\n\n` +
        `Rules:\n${rules}\n\n` +
        `Correction level: ${modeGuide[mode]}\n` +
        `${contextBlock}\n` +
        `Message to correct:\n${sanitizedText}`
    );
}

async function correctWithAI(text: string, replyContext: string | null): Promise<string | null> {
    const apiKey = settings.store.apiKey?.trim();
    if (!apiKey) return null;

    const { sanitized, placeholders } = sanitize(text);
    const replyCtxSanitized = replyContext ? sanitize(replyContext).sanitized : null;
    const prompt = buildPrompt(sanitized, replyCtxSanitized);

    try {
        const response = await fetch("https://api.anthropic.com/v1/messages", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-api-key": apiKey,
                "anthropic-version": "2023-06-01"
            },
            body: JSON.stringify({
                model: "claude-haiku-4-5-20251001",
                max_tokens: 1024,
                messages: [{ role: "user", content: prompt }]
            })
        });

        if (!response.ok) {
            console.warn(`[OpSec] API error ${response.status}: ${response.statusText}`);
            return null;
        }

        const data = await response.json();
        const aiResult: string = data?.content?.[0]?.text?.trim() ?? "";
        if (!aiResult) return null;

        return restore(aiResult, placeholders);
    } catch (err) {
        console.warn("[OpSec] API call failed:", err);
        return null;
    }
}

const CONTRACTIONS: [RegExp, string][] = [
    [/\bdont\b/gi, "don't"],      [/\bcant\b/gi, "can't"],
    [/\bwont\b/gi, "won't"],      [/\bisnt\b/gi, "isn't"],
    [/\barent\b/gi, "aren't"],    [/\bwasnt\b/gi, "wasn't"],
    [/\bwerent\b/gi, "weren't"],  [/\bhasnt\b/gi, "hasn't"],
    [/\bhavent\b/gi, "haven't"],  [/\bhadnt\b/gi, "hadn't"],
    [/\bdoesnt\b/gi, "doesn't"],  [/\bdidnt\b/gi, "didn't"],
    [/\bshouldnt\b/gi, "shouldn't"], [/\bwouldnt\b/gi, "wouldn't"],
    [/\bcouldnt\b/gi, "couldn't"], [/\bneednt\b/gi, "needn't"],
    [/\bmustnt\b/gi, "mustn't"],
    [/\bim\b/gi, "I'm"],    [/\bive\b/gi, "I've"],
    [/\bill\b/gi, "I'll"],  [/\bid\b/gi, "I'd"],
    [/\byoure\b/gi, "you're"],  [/\byouve\b/gi, "you've"],
    [/\byoull\b/gi, "you'll"],  [/\byoud\b/gi, "you'd"],
    [/\bhes\b/gi, "he's"],      [/\bshes\b/gi, "she's"],
    [/\bwere\b/gi, "we're"],    [/\bweve\b/gi, "we've"],
    [/\bwell\b/gi, "we'll"],    [/\bwed\b/gi, "we'd"],
    [/\btheyre\b/gi, "they're"], [/\btheyve\b/gi, "they've"],
    [/\btheyll\b/gi, "they'll"], [/\btheyd\b/gi, "they'd"],
    [/\blets\b/gi, "let's"],    [/\bthats\b/gi, "that's"],
    [/\btheres\b/gi, "there's"], [/\bwhats\b/gi, "what's"],
    [/\bwhos\b/gi, "who's"],
    [/\bwouldve\b/gi, "would've"], [/\bcouldve\b/gi, "could've"],
    [/\bshouldve\b/gi, "should've"],
    [/\byall\b/gi, "y'all"], [/\baint\b/gi, "ain't"],
];

const SLANG_EXPANSIONS: [RegExp, string][] = [
    [/(^|[\s,!?.])ykwim(?=[\s,!?.]|$)/gi, "$1you know what I mean"],
    [/(^|[\s,!?.])afaict(?=[\s,!?.]|$)/gi, "$1as far as I can tell"],
    [/(^|[\s,!?.])afaik(?=[\s,!?.]|$)/gi, "$1as far as I know"],
    [/(^|[\s,!?.])imho(?=[\s,!?.]|$)/gi, "$1in my humble opinion"],
    [/(^|[\s,!?.])ikyfl(?=[\s,!?.]|$)/gi, "$1I know you feel like"],
    [/(^|[\s,!?.])deadass(?=[\s,!?.]|$)/gi, "$1seriously"],
    [/(^|[\s,!?.])note2self(?=[\s,!?.]|$)/gi, "$1note to self"],
    [/(^|[\s,!?.])frfr(?=[\s,!?.]|$)/gi, "$1for real"],
    [/(^|[\s,!?.])srsly(?=[\s,!?.]|$)/gi, "$1seriously"],
    [/(^|[\s,!?.])tyvm(?=[\s,!?.]|$)/gi, "$1thank you very much"],
    [/(^|[\s,!?.])rofl(?=[\s,!?.]|$)/gi, "$1rolling on the floor laughing"],
    [/(^|[\s,!?.])lmao(?=[\s,!?.]|$)/gi, "$1laughing my ass off"],
    [/(^|[\s,!?.])lmfao(?=[\s,!?.]|$)/gi, "$1laughing my fucking ass off"],
    [/(^|[\s,!?.])lol(?=[\s,!?.]|$)/gi, "$1laughing out loud"],
    [/(^|[\s,!?.])thnx(?=[\s,!?.]|$)/gi, "$1thanks"],
    [/(^|[\s,!?.])fomo(?=[\s,!?.]|$)/gi, "$1fear of missing out"],
    [/(^|[\s,!?.])goat(?=[\s,!?.]|$)/gi, "$1greatest of all time"],
    [/(^|[\s,!?.])ttyl(?=[\s,!?.]|$)/gi, "$1talk to you later"],
    [/(^|[\s,!?.])wdym(?=[\s,!?.]|$)/gi, "$1what do you mean"],
    [/(^|[\s,!?.])asap(?=[\s,!?.]|$)/gi, "$1as soon as possible"],
    [/(^|[\s,!?.])iirc(?=[\s,!?.]|$)/gi, "$1if I recall correctly"],
    [/(^|[\s,!?.])highkey(?=[\s,!?.]|$)/gi, "$1high key"],
    [/(^|[\s,!?.])lowkey(?=[\s,!?.]|$)/gi, "$1low key"],
    [/(^|[\s,!?.])no cap(?=[\s,!?.]|$)/gi, "$1no lie"],
    [/(^|[\s,!?.])ngl(?=[\s,!?.]|$)/gi, "$1not gonna lie"],
    [/(^|[\s,!?.])idk(?=[\s,!?.]|$)/gi, "$1I don't know"],
    [/(^|[\s,!?.])tbh(?=[\s,!?.]|$)/gi, "$1to be honest"],
    [/(^|[\s,!?.])imo(?=[\s,!?.]|$)/gi, "$1in my opinion"],
    [/(^|[\s,!?.])btw(?=[\s,!?.]|$)/gi, "$1by the way"],
    [/(^|[\s,!?.])fyi(?=[\s,!?.]|$)/gi, "$1for your information"],
    [/(^|[\s,!?.])yk(?=[\s,!?.]|$)/gi, "$1you know"],
    [/(^|[\s,!?.])irl(?=[\s,!?.]|$)/gi, "$1in real life"],
    [/(^|[\s,!?.])nvm(?=[\s,!?.]|$)/gi, "$1never mind"],
    [/(^|[\s,!?.])hmu(?=[\s,!?.]|$)/gi, "$1hit me up"],
    [/(^|[\s,!?.])lmk(?=[\s,!?.]|$)/gi, "$1let me know"],
    [/(^|[\s,!?.])wtf(?=[\s,!?.]|$)/gi, "$1what the fuck"],
    [/(^|[\s,!?.])wth(?=[\s,!?.]|$)/gi, "$1what the hell"],
    [/(^|[\s,!?.])omg(?=[\s,!?.]|$)/gi, "$1oh my god"],
    [/(^|[\s,!?.])smh(?=[\s,!?.]|$)/gi, "$1shaking my head"],
    [/(^|[\s,!?.])srsly(?=[\s,!?.]|$)/gi, "$1seriously"],
    [/(^|[\s,!?.])srs(?=[\s,!?.]|$)/gi, "$1serious"],
    [/(^|[\s,!?.])rly(?=[\s,!?.]|$)/gi, "$1really"],
    [/(^|[\s,!?.])obvs(?=[\s,!?.]|$)/gi, "$1obviously"],
    [/(^|[\s,!?.])obv(?=[\s,!?.]|$)/gi, "$1obviously"],
    [/(^|[\s,!?.])pov(?=[\s,!?.]|$)/gi, "$1point of view"],
    [/(^|[\s,!?.])fr(?=[\s,!?.]|$)/gi, "$1for real"],
    [/(^|[\s,!?.])pls(?=[\s,!?.]|$)/gi, "$1please"],
    [/(^|[\s,!?.])plz(?=[\s,!?.]|$)/gi, "$1please"],
    [/(^|[\s,!?.])tyvm(?=[\s,!?.]|$)/gi, "$1thank you very much"],
    [/(^|[\s,!?.])tym(?=[\s,!?.]|$)/gi, "$1thank you"],
    [/(^|[\s,!?.])thx(?=[\s,!?.]|$)/gi, "$1thanks"],
    [/(^|[\s,!?.])ty(?=[\s,!?.]|$)/gi, "$1thank you"],
    [/(^|[\s,!?.])np(?=[\s,!?.]|$)/gi, "$1no problem"],
    [/(^|[\s,!?.])nbd(?=[\s,!?.]|$)/gi, "$1no big deal"],
    [/(^|[\s,!?.])sus(?=[\s,!?.]|$)/gi, "$1suspicious"],
    [/(^|[\s,!?.])wym(?=[\s,!?.]|$)/gi, "$1what you mean"],
    [/(^|[\s,!?.])ikr(?=[\s,!?.]|$)/gi, "$1I know right"],
    [/(^|[\s,!?.])wbu(?=[\s,!?.]|$)/gi, "$1what about you"],
    [/(^|[\s,!?.])hbu(?=[\s,!?.]|$)/gi, "$1how about you"],
    [/(^|[\s,!?.])hru(?=[\s,!?.]|$)/gi, "$1how are you"],
    [/(^|[\s,!?.])gtg(?=[\s,!?.]|$)/gi, "$1got to go"],
    [/(^|[\s,!?.])brb(?=[\s,!?.]|$)/gi, "$1be right back"],
    [/(^|[\s,!?.])afk(?=[\s,!?.]|$)/gi, "$1away from keyboard"],
    [/(^|[\s,!?.])cya(?=[\s,!?.]|$)/gi, "$1see you"],
    [/(^|[\s,!?.])abt(?=[\s,!?.]|$)/gi, "$1about"],
    [/(^|[\s,!?.])cap(?=[\s,!?.]|$)/gi, "$1lie"],
    [/(^|[\s,!?.])gg(?=[\s,!?.]|$)/gi, "$1good game"],
    [/(^|[\s,!?.])gm(?=[\s,!?.]|$)/gi, "$1good morning"],
    [/(^|[\s,!?.])gn(?=[\s,!?.]|$)/gi, "$1good night"],
    [/(^|[\s,!?.])wb(?=[\s,!?.]|$)/gi, "$1welcome back"],
    [/(^|[\s,!?.])gl(?=[\s,!?.]|$)/gi, "$1good luck"],
    [/(^|[\s,!?.])hf(?=[\s,!?.]|$)/gi, "$1have fun"],
];

const MISSPELLINGS: [RegExp, string][] = [
    [/\bi\b/g, "I"],
    [/\bteh\b/gi, "the"],          [/\bliek\b/gi, "like"],
    [/\btrynig\b/gi, "trying"],    [/\btryin\b/gi, "trying"],
    [/\brecieve\b/gi, "receive"],  [/\bseperate\b/gi, "separate"],
    [/\boccured\b/gi, "occurred"], [/\bdefinately\b/gi, "definitely"],
    [/\bbasicaly\b/gi, "basically"], [/\btommorow\b/gi, "tomorrow"],
    [/\balot\b/gi, "a lot"],       [/\bgrammer\b/gi, "grammar"],
    [/\buntill\b/gi, "until"],     [/\bimmediatly\b/gi, "immediately"],
    [/\bneccessary\b/gi, "necessary"], [/\bprobly\b/gi, "probably"],
    [/\btruely\b/gi, "truly"],     [/\bnoticable\b/gi, "noticeable"],
    [/\bpersistant\b/gi, "persistent"], [/\bindependant\b/gi, "independent"],
    [/\bacheive\b/gi, "achieve"],  [/\brecomend\b/gi, "recommend"],
    [/\benviroment\b/gi, "environment"],
];

function applyRegexFallback(text: string): string {
    let r = text;
    r = r.replace(/  +/g, " ").trim();
    r = r.replace(/\.{4,}/g, "...").replace(/!!+/g, "!").replace(/\?\?+/g, "?");
    for (const [re, rep] of CONTRACTIONS) r = r.replace(re, rep);
    for (const [re, rep] of MISSPELLINGS) r = r.replace(re, rep);
    if (settings.store.expandSlang) {
        for (const [re, rep] of SLANG_EXPANSIONS) r = r.replace(re, rep);
    }
    r = r.replace(/^([a-z])/, c => c.toUpperCase());
    if (r.length > 4 && !/[.!?...]$/.test(r.trimEnd())) {
        r = r.trimEnd() + ".";
    }
    return r;
}

function applyCustomReplacements(text: string): string {
    const raw = settings.store.customReplacements?.trim() ?? "";
    if (!raw) return text;
    let result = text;
    for (const line of raw.split("\n")) {
        const eq = line.indexOf("=");
        if (eq < 1) continue;
        const word = line.slice(0, eq).trim();
        const rep = line.slice(eq + 1).trim();
        if (!word || !rep) continue;
        try {
            result = result.replace(new RegExp(`\\b${word}\\b`, "gi"), rep);
        } catch { }
    }
    return result;
}

function isProbablyEnglish(text: string): boolean {
    const en = (text.match(/[a-zA-Z]/g) ?? []).length;
    const other = (text.match(/[\u0400-\u04FF\u0600-\u06FF\u4e00-\u9fff\u3040-\u30ff]/g) ?? []).length;
    if (en + other === 0) return true;
    return en / (en + other) > 0.5;
}

function shouldSkip(text: string): boolean {
    if (text.startsWith("/")) return true;
    if (text.trim().length < 1) return true;
    if (/^https?:\/\/\S+$/.test(text.trim())) return true;
    return false;
}

function getReplyContent(msg: any): string | null {
    try {
        const MessageStore =
            (window as any).DiscordModules?.MessageStore ??
            (window as any).Vencord?.Webpack?.Common?.MessageStore;
        if (!MessageStore || !msg?.messageReference?.message_id) return null;
        const ref = MessageStore.getMessage(
            msg.messageReference.channel_id,
            msg.messageReference.message_id
        );
        return ref?.content?.trim() || null;
    } catch {
        return null;
    }
}

export default definePlugin({
    name: "OpSec",
    description: "AI-powered grammar and autocorrect. Only message text is sent to the API, no account data or IDs ever leave your client.",
    authors: [{
        name: "1nject",
        get id() {
            try {
                const user = UserStore.getCurrentUser();
                return BigInt(user?.id ?? "0");
            } catch {
                return 0n;
            }
        }
    }],
    settings,

    async onBeforeMessageSend(_channelId: string, msg: any) {
        if (!settings.store.enable) return;
        if (!msg?.content) return;
        if (shouldSkip(msg.content)) return;
        if (!isProbablyEnglish(msg.content)) return;

        const original = msg.content;
        let corrected: string | null = null;

        if (settings.store.apiKey?.trim()) {
            const reply = getReplyContent(msg);
            corrected = await correctWithAI(original, reply);
        }

        if (!corrected && settings.store.fallbackToRegex) {
            corrected = applyRegexFallback(original);
        }

        if (corrected) {
            corrected = applyCustomReplacements(corrected);
        }

        if (corrected && corrected !== original) {
            msg.content = corrected;
        }
    },

    start() {
        console.log("[OpSec] Started.");
    },

    stop() {
        console.log("[OpSec] Stopped.");
    }
});
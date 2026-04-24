/**
 * Vencord, a Discord client mod
 * Copyright (c) 2025 Vendicated and contributors*
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Component for UI React displaying and managing hidden servers/folders
 * Used by both the Hidden Servers and Hidden Folders settings panels
 *
 * Cleaner implementation instead of being written within index.tsx :) !
 * We now consider Servers & Folders as "items", depending on the type prop we dynamically render the correct UI
*/

import { React } from "@webpack/common";
import { DiscordStores } from "./storesManager";

interface HiddenItemsListProps {
    type: "server" | "folder";
    items: string[];
    onToggle: (id: string) => void;
    onClearAll: () => void;
    onlyHideInStreamEnabled: boolean;
    description: string;
}

interface ItemInfo {
    id: string;
    name: string;
    expanded?: boolean;
    allServerNames?: string[];
}

export function HiddenItemsList({ type, items, onToggle, onClearAll, onlyHideInStreamEnabled, description }: HiddenItemsListProps) {
    const [itemsInfo, setItemsInfo] = React.useState<ItemInfo[]>([]);
    const stores = DiscordStores.getInstance();

    React.useEffect(() => {
        const loadItemsInfo = async () => {
            const itemsWithInfo: ItemInfo[] = [];

            for (const id of items) {
                try {
                    let name = "Unknown";
                    let allServerNames: string[] = [];

                    if (type === "server") {
                        const guild = stores.getGuild(id);
                        name = guild?.name || `Server ${id}`;
                    } else {
                        const guildFolders = stores.getGuildFolders();
                        const folder = guildFolders.find((f: any) =>
                            f.folderId === id || f.id === id
                        );

                        allServerNames = folder?.guildIds?.map((guildId: string) => {
                            const guild = stores.getGuild(guildId);
                            return guild?.name || guildId;
                        }) || [];

                        const displayNames = allServerNames.slice(0, 3);
                        name = displayNames.length > 0
                            ? `Folder (${displayNames.join(", ")}${displayNames.length < allServerNames.length ? "..." : ""})`
                            : `Folder ${id}`;
                    }

                    itemsWithInfo.push({
                        id,
                        name,
                        expanded: false,
                        allServerNames: allServerNames.length > 0 ? allServerNames : undefined
                    });
                } catch (error) {
                    console.warn(`Failed to get name for ${type} ${id}:`, error);
                    itemsWithInfo.push({ id, name: `Unknown ${type}` });
                }
            }

            setItemsInfo(itemsWithInfo);
        };

        loadItemsInfo();
    }, [items, type]);

    const toggleExpand = (itemId: string) => {
        setItemsInfo(prev => prev.map(item =>
            item.id === itemId
                ? { ...item, expanded: !item.expanded }
                : item
        ));
    };

    const isStreamMode = React.useMemo(() => {
        try {
            const stores = DiscordStores.getInstance();
            return stores.isStreamingMode();
        } catch (error) {
            console.warn("Failed to check streaming mode:", error);
            return false;
        }
    }, []);

    const containerStyle = React.useMemo(() => ({
        backgroundColor: "var(--background-secondary)",
    }), []);

    const containerStyle2 = React.useMemo(() => ({
        display: "flex",
        backgroundColor: "var(--background-secondary)",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: "8px"
    }), []);

    const descriptionStyle = React.useMemo(() => ({
        display: "flex",
        flexDirection: "column",
        marginBottom: "8px"
    }), []);

    const headerStyle = React.useMemo(() => ({
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: "16px",
        marginBottom: "8px"
    }), []);

    const buttonStyle = React.useMemo(() => ({
        padding: "4px 8px",
        backgroundColor: "var(--button-danger-background-disabled)",
        color: "white",
        borderRadius: "4px",
        cursor: "pointer",
        fontSize: "16px",
        fontWeight: "500"
    }), []);

    const statusStyle = React.useMemo(() => ({
        padding: "8px",
        backgroundColor: isStreamMode ? "var(--status-positive)" : "var(--status-warning)",
        borderRadius: "4px",
        color: "white",
        textAlign: "center",
        fontSize: "16px",
        fontWeight: "500",
    }), [isStreamMode]);

    const expandButtonStyle = React.useMemo(() => ({
        background: "none",
        border: "none",
        color: "white",
        cursor: "pointer",
        fontSize: "14px"
    }), []);

    return React.createElement("div", { style: containerStyle }, [
        React.createElement("div", { style: containerStyle2 }, [
            React.createElement("div", { style: descriptionStyle }, [
                React.createElement("div", { key: "header", style: headerStyle }, [
                    React.createElement("h3", {
                        key: "title",
                        style: { fontFamily: "var(--font-primary)", color: "var(--text-default)", fontSize: "16px", fontWeight: "500" }
                    }, `Hidden ${type === "server" ? "Servers" : "Folders"}`)
                ]),

                React.createElement("div", {
                    key: "description",
                    style: {
                        fontFamily: "var(--font-primary)",
                        fontSize: "14px",
                        color: "var(--text-default)"
                    }
                }, description),
            ]),

            React.createElement("button", {
                key: "clear-button",
                onClick: onClearAll,
                style: buttonStyle
            }, "Unhide All"),
        ]),

        onlyHideInStreamEnabled && React.createElement("div", {
            key: "stream-status",
            style: statusStyle
        }, isStreamMode
            ? `Streamer Mode ON - ${type === "server" ? "Servers" : "Folders"} are hidden`
            : `Streamer Mode OFF - ${type === "server" ? "Servers" : "Folders"} are visible`
        ),

        React.createElement("div", {
            key: "item-list"
        }, itemsInfo.length === 0
            ? React.createElement("div", {
                style: {
                    fontFamily: "var(--font-primary)",
                    textAlign: "center",
                    color: "var(--text-muted)",
                    padding: "16px"
                }
            }, `No hidden ${type === "server" ? "servers" : "folders"}.`)
            : itemsInfo.map(itemInfo =>
                React.createElement("div", {
                    key: itemInfo.id,
                    style: {
                        padding : "8px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        opacity: onlyHideInStreamEnabled && !isStreamMode ? 0.5 : 1
                    }
                }, [
                    React.createElement("div", {
                        key: "info",
                        style: {
                            display: "flex",
                            flexDirection: "column",
                            flex: 1,
                            marginRight: "12px"
                        }
                    }, [
                        React.createElement("div", {
                            key: "name-row",
                            style: {
                                display: "flex",
                                alignItems: "center",
                                marginBottom: "2px"
                            }
                        }, [
                            React.createElement("span", {
                                key: "name",
                                style: {
                                    fontFamily: "var(--font-primary)",
                                    color: "var(--text-default)",
                                    fontSize: "14px",
                                }
                            }, itemInfo.name),
                            itemInfo.allServerNames && itemInfo.allServerNames.length > 3 && React.createElement("button", {
                                key: "expand-button",
                                onClick: () => toggleExpand(itemInfo.id),
                                style: expandButtonStyle,
                            }, itemInfo.expanded ? "▲" : "▼")
                        ]),
                        React.createElement("span", {
                            key: "id",
                            style: {
                                fontFamily: "var(--font-primary)",
                                color: "var(--text-muted)",
                                fontSize: "14px",
                            }
                        }, `ID: ${itemInfo.id}`),
                        itemInfo.expanded && itemInfo.allServerNames && React.createElement("div", {
                            key: "expanded-list",
                            style: {
                                marginTop: "4px",
                                padding: "4px",
                                backgroundColor: "var(--background-mod-normal)",
                                borderRadius: "4px",
                                fontSize: "12px"
                            }
                        }, [
                            React.createElement("div", {
                                key: "all-servers-title",
                                style: {
                                    fontWeight: "500",
                                    marginBottom: "2px",
                                    color: "var(--text-muted)",
                                    fontFamily: "var(--font-primary)"
                                }
                            }, `All servers (${itemInfo.allServerNames.length}):`),
                            ...itemInfo.allServerNames.map((serverName, index) =>
                                React.createElement("div", {
                                    key: `server-${index}`,
                                    style: {
                                        padding: "1px 0",
                                        color: "var(--text-muted)",
                                        fontFamily: "var(--font-primary)"
                                    }
                                }, `• ${serverName}`)
                            )
                        ])
                    ]),
                    React.createElement("label", {
                        key: "toggle-wrapper",
                        style: {
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            cursor: "pointer"
                        }
                    }, [
                        React.createElement("span", {
                            key: "toggle-label",
                            style: { color: "var(--text-muted)", fontSize: "14px", fontFamily: "var(--font-primary)" }
                        }, "Hidden"),
                        React.createElement("input", {
                            key: "toggle-input",
                            type: "checkbox",
                            checked: true,
                            onChange: () => onToggle(itemInfo.id),
                            style: { cursor: "pointer" }
                        })
                    ])
                ])
            )
        )
    ]);
}

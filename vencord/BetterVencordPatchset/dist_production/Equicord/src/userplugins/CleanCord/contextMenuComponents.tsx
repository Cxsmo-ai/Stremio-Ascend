/*
 * Vencord, a Discord client mod
 * Copyright (c) 2025 Vendicated and contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Component for displaying contextMenu options for hidden servers/folders
 * Provides options to show/hide servers/folders and access CleanCord settings from the server/folder context menu
 * Also allows to display SVGs for visual indicator :) !
 */

import { openPluginModal } from "@components/settings/tabs/plugins/PluginModal";
import { Menu } from "@webpack/common";
import { React } from "@webpack/common";

const iconStyle: React.CSSProperties = {
    width: "20px",
    height: "20px",
    display: "block",
    margin: "auto"
};

const ShowIcon = () => (
    <svg style={iconStyle} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
    </svg>
);

const HideIcon = () => (
    <svg style={iconStyle} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/>
    </svg>
);

const SettingsIcon = () => (
    <svg style={iconStyle} viewBox="0 0 24 24" fill="currentColor">
        <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
    </svg>
);

export function CleanCordContext(
    getHiddenData: () => { servers: string[]; folders: string[] },
    settings: any,
    toggleServer: (serverId: string) => void,
    toggleFolder: (folderId: string) => void
) {
    return function CleanCordContext(children: any[], { guild, folderId }: { guild?: { id: string; name?: string }; folderId?: string }) {
        if (!settings.store.showOptions) return;
        if (!guild && !folderId) return;

        const hiddenData = getHiddenData();
        const isHidden = guild ? hiddenData.servers.includes(guild.id) : hiddenData.folders.includes(folderId);
        const isServer = !!guild;
        const itemType = isServer ? "Server" : "Folder";
        const label = isHidden ? `Unhide ${itemType}` : `Hide ${itemType}`; //We don't really need this btw, but its useful for debugging :) | Also in the case "onlyHideInStream" = true, this behavior needs to stay

        const ToggleIcon = isHidden ? HideIcon : ShowIcon;
        children.push(
            React.createElement(React.Fragment, { key: "clean-cord-context" }, [
                React.createElement(Menu.MenuSeparator, { key: "separator" }),
                React.createElement(Menu.MenuItem, {
                    key: "clean-cord-menu",
                    id: "clean-cord-menu",
                    label: "CleanCord",
                }, [
                    React.createElement(Menu.MenuItem, {
                        key: "clean-cord-toggle",
                        id: "clean-cord-toggle",
                        label: label,
                        icon: ToggleIcon,
                        action: () => {
                            if (guild) {
                                toggleServer(guild.id);
                            } else if (folderId) {
                                toggleFolder(folderId);
                            }
                        }
                    }),
                    React.createElement(Menu.MenuItem, {
                        key: "clean-cord-manage",
                        id: "clean-cord-manage",
                        label: "Manage CleanCord's Settings",
                        icon: SettingsIcon,
                        action: () => {
                            openPluginModal(Vencord.Plugins.plugins.CleanCord);
                        }
                    })
                ])
            ])
        );
    };
}

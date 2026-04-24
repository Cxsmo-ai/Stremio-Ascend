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

export declare function monkeyPatch(what: any, methodName: any, options: any);
export declare function getModule(filter: any, options?: any);
export declare function wrapFilter(filter: any);
export declare const ReactUtils_filler: {
    setup: (DiscordModules: any) => void;
    wrapElement: (element: HTMLElement) => void;
};
export declare class Patcher {
    static before(...args): any;
    static instead(...args): any;
    static after(...args): any;
    static getPatchesByCaller(...args): any;
    static unpatchAll(...args): any;
    static setup(DiscordModules: any): void;
    static makeOverride(patch: any): (...args: any[]) => any;
}

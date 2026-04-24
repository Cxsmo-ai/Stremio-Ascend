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

import "./TransparentButton.css";

import { React, useState } from "@webpack/common";
import type { PropsWithChildren } from "react";

export function TransparentButton({ children, onClick, clicked = false, clickTarget, isToggle = true, onContextMenu = () => { } }: PropsWithChildren<{ onClick: Function, clicked?: boolean, clickTarget?: any; isToggle?: boolean, onContextMenu?: (event: any) => any; }>) {
    const [isHovered, setIsHovered] = useState(false);
    const [isClicked, setIsClicked] = useState(clicked);

    const handleMouseEnter = () => {
        setIsHovered(true);
    };

    const handleMouseLeave = () => {
        setIsHovered(false);
    };

    const handleClick = ev => {
        if (isToggle)
            setIsClicked(!isClicked);
        else {
            const current = isClicked;
            setIsClicked(!current);
            setTimeout(() => {
                setIsClicked(current);
            }, 200);
        }
        onClick && onClick(clickTarget ?? ev);
    };

    return (
        <button
            className={`bv-transparent-button ${isHovered ? "hovered" : ""} ${isClicked ? "clicked" : ""}`}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            onClick={handleClick}
            onContextMenu={onContextMenu}
        >
            {children}
        </button>
    );
}

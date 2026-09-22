/** @odoo-module **/

import { Component, useState, useRef, useExternalListener, onMounted } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";

export class MenuSearchControl extends Component {
    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.rootRef = useRef("root");
        this.inputRef = useRef("searchInput");
        this.resultsListRef = useRef("resultsList");

        this.state = useState({
            query: "",
            isOpen: false,
            results: [],
            selectedIndex: -1,
        });

        // Close search dropdown on click outside
        useExternalListener(window, "click", this.onWindowClick.bind(this));

        // Re-apply live sidebar filter when UI updates or view changes while keeping search query intact
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            if (this.state.query && this.state.query.trim().length > 0) {
                setTimeout(() => {
                    this.filterSidebarMenus(this.state.query);
                }, 60);
            } else {
                setTimeout(() => {
                    this.openActiveMenuAncestors();
                }, 60);
            }
        });

        onMounted(() => {
            if (this.state.query && this.state.query.trim().length > 0) {
                this.filterSidebarMenus(this.state.query);
            } else {
                this.openActiveMenuAncestors();
            }
        });
    }

    getActiveAncestorIds() {
        const currentMenuId = new URLSearchParams(window.location.hash.substring(1)).get("menu_id");
        const currentId = parseInt(currentMenuId);
        if (!currentId) return new Set();

        const allMenus = this.menuService.getAll() || [];
        const parentMap = new Map();
        for (const m of allMenus) {
            if (m && m.children) {
                for (const cId of m.children) {
                    parentMap.set(cId, m.id);
                }
            }
        }

        const activeAncestors = new Set();
        let curr = currentId;
        while (curr && curr !== "root") {
            const pId = parentMap.get(curr);
            if (pId && pId !== "root") {
                activeAncestors.add(pId);
            }
            curr = pId;
        }

        const currentMenu = this.menuService.getMenu(currentId);
        if (currentMenu && currentMenu.appID) {
            activeAncestors.add(currentMenu.appID);
        }

        return activeAncestors;
    }

    openActiveMenuAncestors() {
        const activeAncestorIds = this.getActiveAncestorIds();
        const $sidebar = $("#menu-dropdown");
        if (!$sidebar.length) return;

        activeAncestorIds.forEach((menuId) => {
            const $col = $(`#child_menu_${menuId}`);
            if ($col.length) {
                $col.addClass("show");
                $sidebar.find(`[data-bs-target='#child_menu_${menuId}']`).attr("aria-expanded", "true").addClass("active");
            }
        });
    }

    openMenuAncestors(menuId, appId) {
        const $sidebar = $("#menu-dropdown");
        if (!$sidebar.length) return;

        const allMenus = this.menuService.getAll() || [];
        const parentMap = new Map();
        for (const m of allMenus) {
            if (m && m.children) {
                for (const cId of m.children) {
                    parentMap.set(cId, m.id);
                }
            }
        }

        let currId = parseInt(menuId);
        while (currId && currId !== "root") {
            const pId = parentMap.get(currId);
            if (pId && pId !== "root") {
                const $col = $(`#child_menu_${pId}`);
                if ($col.length) {
                    $col.addClass("show");
                    $sidebar.find(`[data-bs-target='#child_menu_${pId}']`).attr("aria-expanded", "true").addClass("active");
                }
            }
            currId = pId;
        }

        const targetAppId = appId || (this.menuService.getMenu(parseInt(menuId))?.appID);
        if (targetAppId) {
            const $appCol = $(`#child_menu_${targetAppId}`);
            if ($appCol.length) {
                $appCol.addClass("show");
                $sidebar.find(`[data-bs-target='#child_menu_${targetAppId}']`).attr("aria-expanded", "true").addClass("active");
            }
        }
    }

    onWindowClick(ev) {
        if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
            // Close the popup dropdown only; do NOT clear search text or reset sidebar filter
            this.state.isOpen = false;
        }
    }

    onInput(ev) {
        const value = ev.target.value;
        this.state.query = value;

        if (!value.trim()) {
            this.state.isOpen = false;
            this.state.results = [];
            this.state.selectedIndex = -1;
            this.resetSidebarMenus();
            return;
        }

        this.state.results = this.searchMenus(value);
        this.state.isOpen = true;
        this.state.selectedIndex = this.state.results.length > 0 ? 0 : -1;

        // In-place sidebar live filtering and auto-expanding hierarchy
        this.filterSidebarMenus(value);
    }

    onFocus() {
        if (this.state.query && this.state.query.trim().length > 0) {
            this.state.isOpen = true;
            if (this.state.results.length === 0) {
                this.state.results = this.searchMenus(this.state.query);
            }
            this.filterSidebarMenus(this.state.query);
        }
    }

    clearSearch(ev) {
        if (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        }
        this.state.query = "";
        this.state.isOpen = false;
        this.state.results = [];
        this.state.selectedIndex = -1;

        // Restore sidebar menus while keeping active menu hierarchy open
        this.resetSidebarMenus();

        if (this.inputRef.el) {
            this.inputRef.el.value = "";
            this.inputRef.el.focus();
        }
    }

    onItemHover(index) {
        this.state.selectedIndex = index;
    }

    onKeyDown(ev) {
        if (!this.state.isOpen) {
            if (ev.key === "ArrowDown" && this.state.query.trim()) {
                this.state.isOpen = true;
                ev.preventDefault();
            }
            return;
        }

        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.moveSelection(1);
                break;
            case "ArrowUp":
                ev.preventDefault();
                this.moveSelection(-1);
                break;
            case "Enter":
                ev.preventDefault();
                if (this.state.selectedIndex >= 0 && this.state.results[this.state.selectedIndex]) {
                    this.selectMenuItem(this.state.results[this.state.selectedIndex]);
                }
                break;
            case "Escape":
                ev.preventDefault();
                this.state.isOpen = false;
                break;
        }
    }

    moveSelection(direction) {
        const len = this.state.results.length;
        if (len === 0) return;

        let nextIndex = this.state.selectedIndex + direction;
        if (nextIndex < 0) {
            nextIndex = len - 1;
        } else if (nextIndex >= len) {
            nextIndex = 0;
        }

        this.state.selectedIndex = nextIndex;
        this.scrollToSelected();
    }

    scrollToSelected() {
        if (!this.resultsListRef.el) return;
        const selectedEl = this.resultsListRef.el.querySelector(".result-item.selected");
        if (selectedEl) {
            selectedEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
    }

    buildMenuIndex() {
        const allMenus = this.menuService.getAll() || [];
        const menuMap = new Map();
        const parentMap = new Map();

        // 1. Build lookup and parent maps
        for (const menu of allMenus) {
            if (!menu || !menu.id || menu.id === "root") continue;
            menuMap.set(menu.id, menu);
            if (menu.children && Array.isArray(menu.children)) {
                for (const childId of menu.children) {
                    parentMap.set(childId, menu.id);
                }
            }
        }

        // 2. Build flat list with full breadcrumb hierarchy paths
        const indexedItems = [];
        for (const menu of allMenus) {
            if (!menu || !menu.id || menu.id === "root") continue;

            const path = [];
            let currId = menu.id;
            while (currId && currId !== "root") {
                const m = menuMap.get(currId);
                if (!m) break;
                path.unshift(m.name);
                currId = parentMap.get(currId);
            }

            const breadcrumbs = path.slice(0, -1);
            const fullPath = path.join(" › ");

            indexedItems.push({
                id: menu.id,
                name: menu.name,
                actionID: menu.actionID,
                actionModel: menu.actionModel,
                appID: menu.appID,
                xmlid: menu.xmlid || "",
                path: path,
                breadcrumbs: breadcrumbs,
                fullPath: fullPath,
                hasAction: !!menu.actionID,
                isLeaf: !menu.children || menu.children.length === 0,
                rawMenu: menu,
            });
        }

        return indexedItems;
    }

    searchMenus(query) {
        if (!query || !query.trim()) return [];

        const q = query.trim().toLowerCase();
        const tokens = q.split(/\s+/).filter(Boolean);
        const allItems = this.buildMenuIndex();
        const matched = [];

        for (const item of allItems) {
            const nameLower = (item.name || "").toLowerCase();
            const fullPathLower = (item.fullPath || "").toLowerCase();
            const xmlidLower = (item.xmlid || "").toLowerCase();

            // Match all tokens against full path, name, or xmlid
            const matchesAllTokens = tokens.every(
                (token) =>
                    nameLower.includes(token) ||
                    fullPathLower.includes(token) ||
                    xmlidLower.includes(token)
            );

            if (matchesAllTokens) {
                let score = 0;

                // Exact match on menu name
                if (nameLower === q) score += 100;
                // Starts with query
                else if (nameLower.startsWith(q)) score += 60;
                // Contains query as substring
                else if (nameLower.includes(q)) score += 40;

                // Token matched in name
                for (const token of tokens) {
                    if (nameLower.includes(token)) score += 15;
                }

                // Full path relevance
                if (fullPathLower.includes(q)) score += 10;

                // Prioritize actionable leaf menus over container folders
                if (item.hasAction) score += 25;
                if (item.isLeaf) score += 10;

                matched.push({
                    ...item,
                    score,
                });
            }
        }

        // Sort by score descending, then by shorter path length
        matched.sort((a, b) => b.score - a.score || a.fullPath.length - b.fullPath.length);

        return matched.slice(0, 30);
    }

    /**
     * In-place sidebar filtering and auto-expanding hierarchy
     * Expands all parent menus and sub-menus down to matching items and hides non-matching branches.
     * If provided text matches a menu having sub-menu grouping with another level submenu,
     * opens that menu with its inner sub-menus in collapsed state unless a child or active item is within it.
     */
    filterSidebarMenus(query) {
        if (!query || !query.trim()) {
            this.resetSidebarMenus();
            return;
        }

        const q = query.trim().toLowerCase();
        const $sidebar = $("#menu-dropdown");
        if (!$sidebar.length) return;

        // 1. Reset previous search classes
        $sidebar.find(".menu-search-hidden").removeClass("menu-search-hidden");
        $sidebar.find(".menu-search-matched").removeClass("menu-search-matched");
        $sidebar.find(".menu-search-parent-matched").removeClass("menu-search-parent-matched");
        $sidebar.find(".menu-search-open").removeClass("menu-search-open");

        const matchedLiSet = new Set();
        const parentLiSet = new Set();
        const collapseToOpenSet = new Set();
        const collapsesToForceCloseSet = new Set();
        const descendantLiSet = new Set();
        const directlyMatchedAncestorCollapses = new Set();

        // 2. Iterate through all menu links in the sidebar
        const $allLinks = $sidebar.find("a.main_link, a.sub-main-menu, a.child_menus");

        $allLinks.each((_, el) => {
            const $el = $(el);
            const $li = $el.closest("li");

            // Extract clean text from span or anchor
            let text = "";
            const $textSpan = $el.find("span.app_name, span:not(.app_icon):not(.oi):not(.fa)").first();
            if ($textSpan.length) {
                text = $textSpan.text().trim().toLowerCase();
            } else {
                text = $el.text().trim().toLowerCase();
            }

            if (text && text.includes(q)) {
                matchedLiSet.add($li[0]);
                $li.addClass("menu-search-matched");

                const targetSelector = $el.attr("data-bs-target");
                const hasTargetCollapse = targetSelector && targetSelector.startsWith("#child_menu_");
                const $targetCollapse = hasTargetCollapse ? $(targetSelector) : null;

                if ($targetCollapse && $targetCollapse.length) {
                    // Check if this menu grouping contains nested sub-menus (another level of submenu)
                    const hasNestedSubmenus =
                        $targetCollapse.find(".collapse, [id^='child_menu_'], a.sub-main-menu").length > 0;

                    // Open this menu's immediate container
                    collapseToOpenSet.add($targetCollapse[0]);

                    if (hasNestedSubmenus) {
                        // If provided text matches a menu having sub-menu grouping with another level submenu,
                        // candidate inner sub-menus are collapsed unless a descendant also matched directly
                        $targetCollapse.find(".collapse, [id^='child_menu_']").each((_, nestedCollapse) => {
                            collapsesToForceCloseSet.add(nestedCollapse);
                        });
                    }

                    // Keep direct and descendant list items visible inside this menu grouping
                    $targetCollapse.find("li").each((_, dLi) => descendantLiSet.add(dLi));
                }

                // Record parent collapse containers up to root as protected ancestor collapses
                $li.parents("#menu-dropdown .collapse, #menu-dropdown [id^='child_menu_']").each((_, pCollapse) => {
                    directlyMatchedAncestorCollapses.add(pCollapse);
                    collapseToOpenSet.add(pCollapse);
                });

                // Traverse and mark all parent li elements up to root
                $li.parents("#menu-dropdown li").each((_, pLi) => {
                    parentLiSet.add(pLi);
                    $(pLi).addClass("menu-search-parent-matched");
                });
            }
        });

        // Also protect active menu ancestors from being force-closed
        const activeAncestorIds = this.getActiveAncestorIds();
        activeAncestorIds.forEach((menuId) => {
            const colEl = document.getElementById(`child_menu_${menuId}`);
            if (colEl) {
                directlyMatchedAncestorCollapses.add(colEl);
                collapseToOpenSet.add(colEl);
            }
        });

        // Exclude protected ancestors from force-close set
        directlyMatchedAncestorCollapses.forEach((colEl) => {
            collapsesToForceCloseSet.delete(colEl);
        });

        // 3. Remove force-closed collapses from collapseToOpenSet
        collapsesToForceCloseSet.forEach((colEl) => {
            collapseToOpenSet.delete(colEl);
        });

        // 4. Force-collapse un-matched inner sub-menus
        collapsesToForceCloseSet.forEach((colEl) => {
            const $col = $(colEl);
            $col.removeClass("show menu-search-open");
            const colId = $col.attr("id");
            if (colId) {
                $sidebar.find(`[data-bs-target='#${colId}']`).attr("aria-expanded", "false").removeClass("active");
            }
        });

        // 5. Open all valid parent and ancestor collapse containers
        collapseToOpenSet.forEach((colEl) => {
            if (!collapsesToForceCloseSet.has(colEl)) {
                const $col = $(colEl);
                $col.addClass("show menu-search-open");
                const colId = $col.attr("id");
                if (colId) {
                    $sidebar.find(`[data-bs-target='#${colId}']`).attr("aria-expanded", "true");
                }
            }
        });

        // 6. Hide all li items that are neither matched, nor part of a matched parent chain, nor inside a matched branch
        $sidebar.find("li").each((_, liEl) => {
            if (
                !matchedLiSet.has(liEl) &&
                !parentLiSet.has(liEl) &&
                !descendantLiSet.has(liEl)
            ) {
                $(liEl).addClass("menu-search-hidden");
            }
        });

        // 7. If nothing matched in sidebar, close all opened search collapses
        if (matchedLiSet.size === 0) {
            $sidebar.find(".collapse.menu-search-open").removeClass("show menu-search-open");
        }
    }

    /**
     * Restores sidebar menu tree to default state showing all menus,
     * while keeping the active root menu and sub-menus open.
     */
    resetSidebarMenus() {
        const $sidebar = $("#menu-dropdown");
        if (!$sidebar.length) return;

        // Show all menus by removing search filter classes
        $sidebar.find(".menu-search-hidden").removeClass("menu-search-hidden");
        $sidebar.find(".menu-search-matched").removeClass("menu-search-matched");
        $sidebar.find(".menu-search-parent-matched").removeClass("menu-search-parent-matched");

        const activeAncestorIds = this.getActiveAncestorIds();

        // Collapse only dropdowns that are not ancestors of the currently active menu
        $sidebar.find(".collapse, [id^='child_menu_']").each((_, colEl) => {
            const $col = $(colEl);
            const colId = $col.attr("id");
            const menuIdMatch = colId ? colId.replace("child_menu_", "") : null;
            const menuIdNum = menuIdMatch ? parseInt(menuIdMatch) : null;

            if (menuIdNum && activeAncestorIds.has(menuIdNum)) {
                // Keep active ancestor open
                $col.addClass("show");
                $sidebar.find(`[data-bs-target='#${colId}']`).attr("aria-expanded", "true").addClass("active");
            } else {
                $col.removeClass("show menu-search-open");
                if (colId) {
                    $sidebar.find(`[data-bs-target='#${colId}']`).attr("aria-expanded", "false").removeClass("active");
                }
            }
        });
    }

    async selectMenuItem(item) {
        if (!item) return;

        // Close popup dropdown, but RETAIN the entered search text in the search bar
        this.state.isOpen = false;

        // Navigate using menuService or actionService
        try {
            const menu = this.menuService.getMenu(item.id) || item.rawMenu;
            if (menu) {
                await this.menuService.selectMenu(menu);
            } else if (item.actionID) {
                await this.actionService.doAction(item.actionID);
            }
        } catch (error) {
            console.error("Failed to select menu item:", error);
        }

        // Expand all parent and ancestor containers in the sidebar for this item
        try {
            this.openMenuAncestors(item.id, item.appID);
        } catch (_) {}

        // Keep sidebar live filter and expanded path active for the entered search text
        if (this.state.query && this.state.query.trim().length > 0) {
            this.filterSidebarMenus(this.state.query);
        }

        // Mobile responsive: close sidebar drawer if open
        if (window.innerWidth <= 768) {
            $(".nav-wrapper-bits").removeClass("toggle-show");
        }
    }
}

MenuSearchControl.template = "menu_search_bar.MenuSearchControl";
MenuSearchControl.components = {};
MenuSearchControl.props = {};

// Register component on WebClient
patch(WebClient, {
    components: {
        ...WebClient.components,
        MenuSearchControl,
    },
});

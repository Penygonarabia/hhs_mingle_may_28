/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { useService, useBus } from '@web/core/utils/hooks';
import { useState } from '@odoo/owl';
import { patch } from "@web/core/utils/patch";
import { useEnvDebugContext } from "@web/core/debug/debug_context";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.debugContext = useEnvDebugContext();
        this.rpc = useService('rpc');
        this.companyService = useService("company");
        this.currentCompany = this.companyService.currentCompany;
        this.menuService = useService("menu");
        this.navState = useState({ menuId: new URLSearchParams(window.location.hash.substring(1)).get('menu_id') });
        useBus(this.env.bus, 'ACTION_MANAGER:UI-UPDATED', () => {
            this.navState.menuId = new URLSearchParams(window.location.hash.substring(1)).get('menu_id');
        });
    },
    toggleSidebar(ev){
        $(ev.currentTarget).toggleClass('visible');
        $('.nav-wrapper-bits').toggleClass('toggle-show');
    },
    get currentMenuId() {
        return this.navState.menuId;
    },
    hasActiveDescendant(menuId) {
        const currentId = parseInt(this.currentMenuId);
        if (!currentId) return false;
        const check = (id) => {
            if (id === currentId) return true;
            const menu = this.menuService.getMenu(id);
            return (menu?.children || []).some(c => check(c));
        };
        const menu = this.menuService.getMenu(parseInt(menuId));
        return (menu?.children || []).some(c => check(c));
    },
    getBreadcrumbPath() {
        const currentId = parseInt(this.currentMenuId);
        if (!currentId) return [];
        const allMenus = this.menuService.getAll();
        const parentMap = new Map();
        for (const menu of allMenus) {
            for (const childId of (menu.children || [])) {
                parentMap.set(childId, menu.id);
            }
        }
        const path = [];
        let id = currentId;
        while (id && id !== 'root') {
            const menu = this.menuService.getMenu(id);
            if (!menu || menu.id === 'root') break;
            path.unshift({ id: menu.id, name: menu.name });
            id = parentMap.get(id);
        }
        return path;
    },
});
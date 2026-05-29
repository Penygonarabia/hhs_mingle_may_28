/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { KsHeader } from "@ks_dashboard_ninja/components/Header/Header";
import { _t } from "@web/core/l10n/translation";
import { ModalDialog } from '@ks_dn_advance/js/play_modal';

patch(KsHeader.prototype,{
    setup(){
        super.setup();
        let dropdowns_to_add = [
            {name: "Dashboard TV", svg: "dashboard_tv", func:() => this.startTvDashboard(), class : '', modes: ["manager", "user", "custom_date"],},
            {name: "Email", svg: "email_svg", func:() => this.ks_send_mail(), class : '', modes: ["manager","user", "custom_date"],},
            {name: "Print Dashboard", svg: "print_dashboard", func:() => this.ks_dash_print(), class : '', modes: ["manager","user", "custom_date"],},
        ]
        let last_dropdown = this.dropdowns.find( (dropdown) => dropdown.name === 'More')
        last_dropdown.dropdown_items.push(...dropdowns_to_add)
    },

    _patchElementStyles() {
        console.log("=== _patchElementStyles: STARTING OVERRIDES ===");
        const snapshots = [];
        
        // Dynamic style to hide pseudo-element :before rules during canvas render,
        // forcing html2canvas to render our copied innerText unicode glyph instead!
        // We will append it to the head at the very end of this method AFTER extracting the glyphs!
        const hideBeforeStyle = document.createElement('style');
        hideBeforeStyle.id = 'html2canvas-hide-before-style';
        hideBeforeStyle.innerHTML = `
            .ks_dashboard_icon_l5 span::before, 
            .ks_dashboard_icon_l5 i::before {
                content: none !important;
                display: none !important;
            }
        `;
        
        function patchStyle(el, styles, textContent, htmlContent) {
            const original = el.style.cssText;
            for (const key in styles) {
                let value = styles[key];
                let priority = '';
                if (typeof value === 'string' && value.includes('!important')) {
                    value = value.replace('!important', '').trim();
                    priority = 'important';
                }
                const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
                el.style.setProperty(cssKey, value, priority);
            }
            snapshots.push({ el, original, text: textContent, html: htmlContent });
        }

        // 1. Get the main container and its screen bounding box (to calculate relative coordinates)
        const container = document.querySelector('.ks_dashboard_item_content');
        let containerRect = { top: 0, left: 0, width: 1200 };
        if (container) {
            containerRect = container.getBoundingClientRect();
        }

        // 2. Sort and group all grid stack items into rows, aligning them perfectly with landscape page boundaries
        const gridItems = document.querySelectorAll('.ks_dashboard_item_content .grid-stack-item');
        console.log("=== _patchElementStyles: Sorting and grouping", gridItems.length, "gridItems into rows");
        
        // Convert to array and sort by physical screen top coordinate to ensure top-to-bottom processing
        const sortedItems = Array.from(gridItems).sort(function (a, b) {
            return a.getBoundingClientRect().top - b.getBoundingClientRect().top;
        });

        // 297mm x 210mm A4 landscape page scale height in pixels
        const PAGE_HEIGHT_PX = 210 * (containerRect.width / 297);
        console.log("=== _patchElementStyles: Calculated PAGE_HEIGHT_PX =", PAGE_HEIGHT_PX);

        // Group sorted items into rows based on top coordinate proximity (e.g., within 30px of each other)
        const rows = [];
        sortedItems.forEach(function (gridItem) {
            const rect = gridItem.getBoundingClientRect();
            const originalTop = rect.top - containerRect.top;
            const originalHeight = rect.height;
            
            // Try to find an existing row whose top is within 30px
            let foundRow = null;
            for (let i = 0; i < rows.length; i++) {
                if (Math.abs(rows[i].originalTop - originalTop) < 30) {
                    foundRow = rows[i];
                    break;
                }
            }
            
            const itemData = {
                el: gridItem,
                rect: rect,
                originalTop: originalTop,
                originalHeight: originalHeight
            };
            
            if (foundRow) {
                foundRow.items.push(itemData);
                // Update row's maximum height
                if (originalHeight > foundRow.maxHeight) {
                    foundRow.maxHeight = originalHeight;
                }
            } else {
                rows.push({
                    originalTop: originalTop,
                    maxHeight: originalHeight,
                    items: [itemData]
                });
            }
        });

        // Align each row to avoid cutting items across page boundaries
        let pushedOffset = 0;
        let maxBottom = 0;

        rows.forEach(function (row) {
            let rowTop = row.originalTop + pushedOffset;
            const rowHeight = row.maxHeight;

            // Page alignment check: if the row fits on a single page but would cross a page boundary,
            // push the entire row down to start exactly at the top of the next page!
            if (rowHeight < PAGE_HEIGHT_PX) {
                const startPage = Math.floor(rowTop / PAGE_HEIGHT_PX);
                const endPage = Math.floor((rowTop + rowHeight) / PAGE_HEIGHT_PX);
                
                if (startPage !== endPage) {
                    const nextPageStart = (startPage + 1) * PAGE_HEIGHT_PX;
                    const push = nextPageStart - rowTop;
                    pushedOffset += push;
                    rowTop = nextPageStart;
                    console.log("=== _patchElementStyles: Pushing entire row crossing page boundary. Push:", push, "New Row Top:", rowTop);
                }
            }

            // Apply style overrides to all items in this row
            row.items.forEach(function (item) {
                // To preserve slight vertical offsets inside the row,
                // we apply the row's pushed top but keep the item's original relative offset
                const relativeOffset = item.originalTop - row.originalTop;
                const finalTop = rowTop + relativeOffset;

                patchStyle(item.el, {
                    position: 'absolute !important',
                    top: finalTop + 'px !important',
                    left: (item.rect.left - containerRect.left) + 'px !important',
                    height: item.originalHeight + 'px !important',
                    width: item.rect.width + 'px !important',
                    transform: 'none !important', // Reset transformation to prevent html2canvas scaling issues
                    overflow: 'visible !important',
                    fontFamily: 'Arial, Helvetica, sans-serif !important',
                    boxSizing: 'border-box !important'
                });

                const itemBottom = finalTop + item.originalHeight;
                if (itemBottom > maxBottom) {
                    maxBottom = itemBottom;
                }

                // Inner chart body styling (natural original sizing, preventing collapsing!)
                const chartBody = item.el.querySelector('.ks_chart_card_body');
                if (chartBody) {
                    patchStyle(chartBody, {
                        height: 'calc(100% - 60px) !important',
                        minHeight: 'auto !important',
                        maxHeight: 'none !important',
                        overflow: 'visible !important',
                        position: 'relative !important'
                    });
                    
                    const chartCanvas = chartBody.querySelector('canvas, svg');
                    if (chartCanvas) {
                        patchStyle(chartCanvas, {
                            height: '100% !important',
                            width: '100% !important',
                            maxHeight: '100% !important',
                            display: 'block !important'
                        });
                    }
                }

                // List view table scrollable/visible heights
                const listTable = item.el.querySelector('.ks_list_item_table');
                if (listTable) {
                    patchStyle(listTable, {
                        height: 'calc(100% - 60px) !important',
                        minHeight: 'auto !important',
                        maxHeight: 'none !important',
                        overflow: 'visible !important'
                    });
                }
            });
        });

        // 3. Freeze the main container width and set its height to the true maxBottom (fully expanded, no truncation)
        if (container) {
            const finalHeight = maxBottom > 0 ? (maxBottom + 20) : containerRect.height;
            console.log("=== _patchElementStyles: Setting container frozen height to:", finalHeight, "width:", containerRect.width);
            patchStyle(container, {
                height: finalHeight + 'px !important',
                width: containerRect.width + 'px !important',
                position: 'relative !important',
                overflow: 'visible !important',
                fontFamily: 'Arial, Helvetica, sans-serif !important'
            });
        }

        // 3. Style KPI tiles with screen-accurate absolute stretch and hardcoded high-contrast colors (bypassing CSS variable bugs)
        const tiles = document.querySelectorAll('.ks_dashboard_kpi');
        console.log("=== _patchElementStyles: Processing", tiles.length, "KPI tiles");
        tiles.forEach(function (tile) {
            const item = tile.classList.contains('ks_dashboarditem_id')
                ? tile
                : tile.querySelector('.ks_dashboarditem_id');

            if (!item) return;

            // Calculate luminance of computed background color to dynamically determine correct text contrast
            const computedStyle = window.getComputedStyle(item);
            const bgColor = computedStyle.backgroundColor || 'rgba(0,0,0,0)';
            
            let isDark = true;
            if (bgColor) {
                const match = bgColor.match(/rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i) || 
                              bgColor.match(/rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
                if (match) {
                    const r = parseInt(match[1], 10);
                    const g = parseInt(match[2], 10);
                    const b = parseInt(match[3], 10);
                    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                    if (luminance > 0.65) {
                        isDark = false; // Light background, use dark text
                    }
                }
            }

            const cardFontColor = isDark ? '#ffffff' : '#333333';

            // Maintain the tile's absolute stretching inside the parent grid item with a beautiful gutter/space (e.g. 6px) to match live screen!
            patchStyle(item, {
                display: 'block !important',
                position: 'absolute !important',
                top: '6px !important',
                left: '6px !important',
                right: '6px !important',
                bottom: '6px !important',
                width: 'auto !important',
                height: 'auto !important',
                color: cardFontColor + ' !important',
                backgroundColor: bgColor + ' !important',
                fontFamily: 'Arial, Helvetica, sans-serif !important',
                boxSizing: 'border-box !important',
                overflow: 'visible !important',
                padding: '24px 8px 8px 8px !important' // leave room for corner icon
            });

            // Clean up the main body container to prevent collapsing
            const bodyEl = item.querySelector('.ks_dashboard_item_main_body_l5');
            let flexEl = item.querySelector('.flex-container');
            let isWrapped = false;

            // If there's no flex-container, dynamically wrap the bodyEl in a .flex-container
            // so all KPI cards (single-value, two-value, 2-model, etc.) share the exact same DOM structure and alignment!
            if (!flexEl && bodyEl) {
                const wrapper = document.createElement('div');
                wrapper.className = 'flex-container';
                const parent = bodyEl.parentNode;
                parent.insertBefore(wrapper, bodyEl);
                wrapper.appendChild(bodyEl);
                flexEl = wrapper;
                isWrapped = true;
                
                snapshots.push({
                    isWrapping: true,
                    wrapper: wrapper,
                    body: bodyEl
                });
            }

            const hasProgress = item.querySelector('.ks_progress') !== null;

            if (bodyEl) {
                const bodyMarginTop = flexEl ? '0px !important' : '25px !important';
                patchStyle(bodyEl, {
                    display: 'block !important',
                    position: 'relative !important',
                    width: '100% !important',
                    padding: '0 !important',
                    marginTop: bodyMarginTop, // Apply 25px top margin if no flex-container exists
                    textAlign: 'center !important',
                    fontFamily: 'Arial, Helvetica, sans-serif !important'
                });
            }

            if (flexEl) {
                // Progress-bar cards have an extra element at the bottom, so push down by 38px to achieve alignment.
                // Wrapped KPI cards (2-model) require a custom shift of 27px to offset the span element differences.
                // Otherwise, standard single-value KPI cards get a 25px top margin.
                let flexMarginTop = '25px !important';
                if (hasProgress) {
                    flexMarginTop = '38px !important';
                } else if (isWrapped) {
                    flexMarginTop = '27px !important';
                }

                patchStyle(flexEl, {
                    display: 'flex !important',
                    flexDirection: 'row !important',
                    justifyContent: 'center !important',
                    alignItems: 'center !important',
                    width: '100% !important',
                    marginTop: flexMarginTop,
                    gap: '12px !important',
                    fontFamily: 'Arial, Helvetica, sans-serif !important'
                });
            }

            // Style the Icon container: Floating on top in the corner
            const iconEl = item.querySelector('.ks_dashboard_icon_l5');
            if (iconEl) {
                const circleSize = 36;
                patchStyle(iconEl, {
                    position: 'absolute !important',
                    top: '8px !important',
                    left: '8px !important',
                    display: 'flex !important',
                    alignItems: 'center !important',
                    justifyContent: 'center !important',
                    backgroundColor: '#ffffff !important',
                    width: circleSize + 'px !important',
                    height: circleSize + 'px !important',
                    borderRadius: '50% !important',
                    visibility: 'visible !important',
                    opacity: '1 !important',
                    zIndex: '999 !important',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1) !important',
                    margin: '0 !important',
                    padding: '0 !important',
                    border: 'none !important',
                    boxSizing: 'border-box !important'
                });

                // Style the FontAwesome icon span/i inside it
                const iconSpan = iconEl.querySelector('span, i');
                if (iconSpan) {
                    let iconColor = bgColor;
                    if (iconColor === 'rgba(0,0,0,0)' || iconColor === 'transparent') {
                        iconColor = '#333333';
                    }

                    const origHTML = iconSpan.innerHTML;

                    // Replace with the exact, authentic FontAwesome speech bubble with three dots
                    // that is guaranteed to render perfectly in html2canvas without CORS or FontAwesome loading bugs!
                    // Nested inside zero-padding flex containers to achieve absolute, mathematical dead-center alignment!
                    iconSpan.innerHTML = `
                        <svg viewBox="0 0 512 512" fill="${iconColor}" xmlns="http://www.w3.org/2000/svg" style="width: 22px !important; height: 22px !important; margin: 0 !important; padding: 0 !important; display: block !important; border: none !important; box-sizing: border-box !important; flex-shrink: 0 !important;">
                            <path d="M256 32C114.6 32 0 125.1 0 240c0 49.6 21.4 95 57 130.7c-9.2 41.4-31.2 92.8-31.8 94.2c-2.3 5.3-.2 11.5 5.1 14.1c1.7 .9 3.5 1.3 5.4 1.3c3.8 0 7.5-1.7 10.1-4.8c1.9-2.3 39-47 75.3-70.3C161.4 430.7 207.1 448 256 448c141.4 0 256-93.1 256-208S397.4 32 256 32zm-128 240c-17.7 0-32-14.3-32-32s14.3-32 32-32s32 14.3 32 32s-14.3 32-32 32zm128 0c-17.7 0-32-14.3-32-32s14.3-32 32-32s32 14.3 32 32s-14.3 32-32 32zm128 0c-17.7 0-32-14.3-32-32s14.3-32 32-32s32 14.3 32 32s-14.3 32-32 32z" />
                        </svg>
                    `;

                    patchStyle(iconSpan, {
                        display: 'flex !important',
                        alignItems: 'center !important',
                        justifyContent: 'center !important',
                        position: 'relative !important',
                        top: 'auto !important',
                        left: 'auto !important',
                        width: '100% !important',
                        height: '100% !important',
                        margin: '0 !important',
                        padding: '0 !important',
                        border: 'none !important',
                        boxSizing: 'border-box !important',
                        color: iconColor + ' !important',
                        visibility: 'visible !important',
                        opacity: '1 !important',
                        zIndex: '1000 !important'
                    }, undefined, origHTML);
                }

                // Custom image icon
                const iconImg = iconEl.querySelector('img');
                if (iconImg) {
                    patchStyle(iconImg, {
                        display: 'block !important',
                        width: '20px !important',
                        height: '20px !important',
                        margin: 'auto !important',
                        visibility: 'visible !important',
                        zIndex: '1000 !important'
                    });
                }
            }

            // Fix Count / Value text: force dynamic color, block layout, full width, and visible overflow
            const countEl = item.querySelector('.ks_dashboard_kpi_count_preview');
            if (countEl) {
                patchStyle(countEl, {
                    display: 'block !important',
                    position: 'relative !important',
                    width: '100% !important',
                    overflow: 'visible !important',
                    color: cardFontColor + ' !important',
                    fontSize: '28px !important',
                    fontWeight: 'bold !important',
                    margin: '4px auto !important',
                    textAlign: 'center !important',
                    visibility: 'visible !important',
                    opacity: '1 !important',
                    zIndex: '999 !important',
                    fontFamily: 'Arial, Helvetica, sans-serif !important',
                    lineHeight: '1.2 !important'
                });
                countEl.querySelectorAll('*').forEach(function (c) {
                    patchStyle(c, {
                        color: cardFontColor + ' !important',
                        display: 'inline !important',
                        visibility: 'visible !important',
                        opacity: '1 !important',
                        zIndex: '1000 !important',
                        fontFamily: 'Arial, Helvetica, sans-serif !important',
                        lineHeight: '1.2 !important'
                    });
                });
            }

            // Fix KPI Name / Title label: force dynamic color, block layout, full width, and visible overflow (with !important to override justify)
            const nameEl = item.querySelector('.ks_dashboard_kpi_name_preview');
            if (nameEl) {
                patchStyle(nameEl, {
                    display: 'block !important',
                    position: 'relative !important',
                    width: '100% !important',
                    overflow: 'visible !important',
                    color: cardFontColor + ' !important',
                    fontSize: '14px !important',
                    margin: '16px auto 0 auto !important', // Beautiful 16px space between value and heading!
                    textAlign: 'center !important',
                    whiteSpace: 'nowrap !important',
                    visibility: 'visible !important',
                    opacity: '1 !important',
                    zIndex: '999 !important',
                    fontFamily: 'Arial, Helvetica, sans-serif !important'
                });
            }

            // Style deviation labels
            ['var-prev', 'pre_deviation', 'target_deviation', 'ks_target_previous'].forEach(function (cls) {
                const el = item.querySelector('.' + cls);
                if (el) {
                    patchStyle(el, {
                        color: cardFontColor + ' !important',
                        fontSize: '12px !important',
                        visibility: 'visible !important',
                        opacity: '1 !important',
                        zIndex: '999 !important',
                        fontFamily: 'Arial, Helvetica, sans-serif !important',
                        textAlign: 'center !important'
                    });
                    el.querySelectorAll('*').forEach(function (c) {
                        patchStyle(c, {
                            color: cardFontColor + ' !important',
                            visibility: 'visible !important',
                            opacity: '1 !important',
                            zIndex: '1000 !important'
                        });
                    });
                }
            });
        });

        // 4. Style all chart headings, list headings, and to-do headings with a solid high-contrast deep navy theme color
        // Widen the selector to cover both container-scoped and global headings, including any standard heading tags under headers
        const headings = document.querySelectorAll(
            '.ks_dashboard_item_content .ks_chart_heading, ' +
            '.ks_dashboard_item_content .ks_list_view_heading, ' +
            '.ks_dashboard_item_content .dashboard-header h4, ' +
            '.ks_dashboard_item_content .dashboard-header h6, ' +
            '.ks_chart_heading, ' +
            '.ks_list_view_heading'
        );
        console.log("=== _patchElementStyles: Processing", headings.length, "chart/list headings");
        headings.forEach(function (heading) {
            // Force high contrast, non-collapsible sizing and visibility to bypass html2canvas layout bugs.
            // If the element uses white-space: nowrap with overflow: hidden or percentage widths,
            // html2canvas might collapse its width to 0px in the cloned sandbox. Setting width: auto,
            // min-width: max-content, overflow: visible guarantees the text prints fully.
            patchStyle(heading, {
                color: '#05004e !important',
                visibility: 'visible !important',
                opacity: '1 !important',
                display: 'block !important',
                fontFamily: 'Arial, Helvetica, sans-serif !important',
                width: 'auto !important',
                minWidth: 'max-content !important',
                maxWidth: 'none !important',
                overflow: 'visible !important',
                whiteSpace: 'nowrap !important',
                textOverflow: 'unset !important'
            });

            // Also force-expand the immediate parent wrapper (which often has a collapsing w-50 or flex class)
            const parentEl = heading.parentElement;
            if (parentEl) {
                patchStyle(parentEl, {
                    width: 'auto !important',
                    minWidth: 'max-content !important',
                    maxWidth: 'none !important',
                    overflow: 'visible !important',
                    display: 'flex !important',
                    visibility: 'visible !important',
                    opacity: '1 !important'
                });
            }
        });

        // 5. Ensure all dashboard item headers are visible and not hidden by print classes or hover styles
        const headers = document.querySelectorAll('.ks_dashboard_item_content .dashboard-header, .dashboard-header');
        console.log("=== _patchElementStyles: Processing", headers.length, "dashboard headers");
        headers.forEach(function (header) {
            patchStyle(header, {
                display: 'flex !important',
                visibility: 'visible !important',
                opacity: '1 !important',
                backgroundColor: 'transparent !important',
                color: '#05004e !important',
                width: '100% !important',
                overflow: 'visible !important'
            });
        });

        console.log("=== _patchElementStyles: OVERRIDES COMPLETED ===");
        
        // Append the pseudo-element suppressor stylesheet AFTER extracting all unicode characters
        // so that window.getComputedStyle returns the real FontAwesome glyphs!
        document.head.appendChild(hideBeforeStyle);
        
        return snapshots;
    },

    _restoreElementStyles(snapshots) {
        console.log("=== _restoreElementStyles: RESTORING ORIGINAL STYLES ===");
        // Remove the temporary html2canvas pseudo-element stylesheet
        const hideBeforeStyle = document.getElementById('html2canvas-hide-before-style');
        if (hideBeforeStyle) {
            hideBeforeStyle.remove();
        }
        if (snapshots) {
            // Restore in reverse order to cleanly undo wrapping and styles
            for (let i = snapshots.length - 1; i >= 0; i--) {
                const s = snapshots[i];
                if (s.isWrapping) {
                    if (s.wrapper && s.body && s.wrapper.parentNode) {
                        s.wrapper.parentNode.insertBefore(s.body, s.wrapper);
                        s.wrapper.parentNode.removeChild(s.wrapper);
                    }
                } else if (s.el) {
                    s.el.style.cssText = s.original;
                    if (s.text !== undefined) {
                        s.el.innerText = s.text;
                    }
                    if (s.html !== undefined) {
                        s.el.innerHTML = s.html;
                    }
                }
            }
        }
    },

        ks_dash_print(id){
            console.log("=== ks_dash_print: PRINT ACTION TRIGGERED ===");
            var self = this;
            var ks_dashboard_name = self.ks_dashboard_data.name
            setTimeout(function () {
            window.scrollTo(0, 0);
            var snapshots = self._patchElementStyles();
            console.log("=== ks_dash_print: RUNNING html2canvas ===");
            html2canvas(document.querySelector('.ks_dashboard_item_content'), {useCORS: true, allowTaint: false}).then(function(canvas){
            console.log("=== ks_dash_print: html2canvas FINISHED, GENERATING PDF ===");
            self._restoreElementStyles(snapshots);
            window.jsPDF = window.jspdf.jsPDF;
            var pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a4'
            });
            var ks_img = canvas.toDataURL("image/jpeg", 0.90);
            var ks_props= pdf.getImageProperties(ks_img);
            var KspageWidth = pdf.internal.pageSize.getWidth();
            var KspageHeight = pdf.internal.pageSize.getHeight();
            var ksheight = (ks_props.height * KspageWidth) / ks_props.width;
            var ksheightLeft = ksheight;
            var position = 0;

            pdf.addImage(ks_img,'JPEG', 0, 0, KspageWidth, ksheight, 'FAST');
            ksheightLeft -= KspageHeight;
            while (ksheightLeft >= 0) {
                position = ksheightLeft - ksheight;
                pdf.addPage('a4', 'l');
                pdf.addImage(ks_img, 'JPEG', 0, position,  KspageWidth, ksheight, 'FAST');
                ksheightLeft -= KspageHeight;
            };
            pdf.save(ks_dashboard_name + '.pdf');
            console.log("=== ks_dash_print: PDF SAVED SUCCESSFULLY ===");
        }).catch(function(err) {
            self._restoreElementStyles(snapshots);
            console.error("=== ks_dash_print: ERROR IN html2canvas ===", err);
        });
        },500);
        },


        ks_send_mail(ev) {
            console.log("=== ks_send_mail: EMAIL ACTION TRIGGERED ===");
            var self = this;
            var ks_dashboard_name = self.ks_dashboard_data.name
            setTimeout(function () {
            $('.fa-envelope').addClass('d-none')
            $('.fa-spinner').removeClass('d-none');


            window.scrollTo(0, 0);
            var snapshots = self._patchElementStyles();
            html2canvas(document.querySelector('.ks_dashboard_item_content'), {useCORS: true, allowTaint: false}).then(function(canvas){
            self._restoreElementStyles(snapshots);
            window.jsPDF = window.jspdf.jsPDF;
            var pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a4'
            });
            var ks_img = canvas.toDataURL("image/jpeg", 0.90);
            var ks_props= pdf.getImageProperties(ks_img);
            var KspageWidth = pdf.internal.pageSize.getWidth();
            var KspageHeight = pdf.internal.pageSize.getHeight();
            var ksheight = (ks_props.height * KspageWidth) / ks_props.width;
            var ksheightLeft = ksheight;
            var position = 0;

            pdf.addImage(ks_img,'JPEG', 0, 0, KspageWidth, ksheight, 'FAST');
            ksheightLeft -= KspageHeight;
            while (ksheightLeft >= 0) {
                position = ksheightLeft - ksheight;
                pdf.addPage('a4', 'l');
                pdf.addImage(ks_img, 'JPEG', 0, position,  KspageWidth, ksheight, 'FAST');
                ksheightLeft -= KspageHeight;
            };
//            pdf.save(ks_dashboard_name + '.pdf');
            const file = pdf.output()
            const base64String = btoa(file)

//            localStorage.setItem(ks_dashboard_name + '.pdf',file);

            $.when(base64String).then(function(){
                self._rpc("/web/dataset/call_kw/ks_dashboard_ninja.board/ks_dashboard_send_mail",{
                    model: 'ks_dashboard_ninja.board',
                    method: 'ks_dashboard_send_mail',
                    args: [
                        [parseInt(self.ks_dashboard_id)],base64String

                    ],

                    kwargs:{}
                }).then(function(res){
                    $('.fa-envelope').removeClass('d-none')
                    $('.fa-spinner').addClass('d-none');
                    if (res['ks_is_send']){
                        var msg = res['ks_massage']
                            self.notification.add(_t(msg),{
                                title:_t("Success"),
                                type: 'info',
                            });

                    }else{
                        var msg = res['ks_massage']
                        self.notification.add(_t(msg),{
                                title:_t("Fail"),
                                type: 'warning',
                            });

                    }
                });
             })
        }).catch(function(err) {
            self._restoreElementStyles(snapshots);
            $('.fa-envelope').removeClass('d-none');
            $('.fa-spinner').addClass('d-none');
            console.error(err);
        });
        },500);

        },

        startTvDashboard(e){
            if(this.checkItemsPresence())   return;
            var self = this;
            this.dialogService.add(ModalDialog,{
                items : Object.values(self.ks_dashboard_data.ks_item_data),
                dashboard_data : self.ks_dashboard_data,
                ksdatefilter:'none',
                pre_defined_filter : {},
                custom_filter:{},
                close: () => {},
                getDomainParams: this.env.ksGetParamsForItemFetch,
                getDashboardContext: this.env.getContext,

            });
        },


});


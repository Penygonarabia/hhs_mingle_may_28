/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, onMounted, useRef, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class EmployeeOrgChart extends Component {
    static props = ["*"];
    static template = "organization_chart.orgchart";

    setup() {
        this.user = useService("user");
        this.company = useService("company");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.dialog = useService('dialog');
        this.actionService = useService("action");
        this.searchInputRef = useRef("search_input");
        this.chartContainertRef = useRef("chart_container");

        this.state = useState({
            direction: 't2b',
            employee_data: [],
            orgchart: false,
        });

        onWillStart(async () => {
            this.is_hr_user = await this.user.hasGroup("hr.group_hr_manager");
            this.is_hr_manager = await this.user.hasGroup("hr.group_hr_user");
            await this.fetch_data();
        });
        onMounted(async () => {
            await this.render_orgchart();
        });
        browser.addEventListener("resize", this._onResize.bind(this));
    }
    async fetch_data() {
        var self = this;
        var result = await self.rpc('/orgchart/getdata', {
            company_id: self.company.currentCompany.id || false,
        });

        if (result && result.data) {
            self.state.employee_data = result.data;
        }
        return;
    }
    render_orgchart(event) {
        var self = this;
        var nodeTemplate = function (data) {
            if (data._name === 'hr.employee') {
                if (self.direction == 't2b') {
                    return `
                        <div class="title">${data.name}</div>
                        <div class="content">
                            <span class="photo">
                                <img class="img" src="/web/image?model=hr.employee&amp;field=image_1920&amp;id=${data.id}" style="width: 128px;height: 128px;"/>
                            </span>
                            <span style="min-height: 35px; display: flex; justify-content: center; align-items: center; background-color: #cecece47;">
                                ${data.title}
                            </span>
                        </div>
                    `;
                } else {
                    return `
                        <div class="title">${data.name}</div>
                        <div class="content">
                            <span style="min-height: 35px; display: flex; justify-content: center; align-items: center; background-color: #cecece47;">
                                ${data.title}
                            </span>
                        </div>
                    `;
                }
                //  <div class="title">${data.name}</div>
                // <div class="content">
                //     <span style="min-height: 35px; display: flex; justify-content: center; align-items: center; background-color: #cecece47;">
                //         ${data.title}
                //     </span>
                // </div>
            } else if (data._name === 'res.company') {
                if (self.direction == 't2b') {
                    return `
                        <div class="title">${data.name}</div>
                        <div class="content">
                            <span class="photo">
                                <img class="img" src="/web/image?model=res.company&amp;field=logo&amp;id=${Math.abs(data.id)}" style="height: 100%;width: 100%;object-fit: contain;"/>
                            </span>
                            <span style="min-height: 35px; display: flex; justify-content: center; align-items: center; background-color: #cecece47;">
                                ${data.title}
                            </span>
                        </div>
                    `;
                } else {
                    return `
                        <div class="title">${data.name}</div>
                        <div class="content">
                            <span style="min-height: 35px; display: flex; justify-content: center; align-items: center; background-color: #cecece47;">
                                ${data.title}
                            </span>
                        </div>
                    `;
                }
            }
        };

        self.state.orgchart = $(this.chartContainertRef.el).orgchart({
            'data': self.state.employee_data,
            'nodeTemplate': nodeTemplate,
            'nodeContent': 'title',
            'toggleSiblingsResp': false,
            'draggable': self.is_hr_manager ? true : false,
            'verticalLevel': 10,
            'visibleLevel': 2,
            'pan': true,
            'zoom': false,
            'dropCriteria': function ($draggedNode, $dragZone, $dropZone) {
                if ($draggedNode.find('.content').text().indexOf('manager') > -1 && $dropZone.find('.content').text().indexOf('engineer') > -1) {
                    return false;
                }
                return true;
            },

            'createNode': function ($node, data) {
                var secondMenuIcon = $('<i>', {
                    'class': 'oci oci-info-circle second-menu-icon',
                    click: function () {
                        $(this).siblings('.second-menu').toggle();
                    }
                });
                var secondMenu = '<div class="second-menu">';
                secondMenu += '<img class="avatar add_node" id="' + data.id + '"src="/organization_chart/static/src/img/add.png"">';
                secondMenu += '<img class="avatar edit_node" id="' + data.id + '"src="/organization_chart/static/src/img/edit.png"">';
                secondMenu += '<img class="avatar delete_node" id="' + data.id + '"src="/organization_chart/static/src/img/delete.png"">';
                secondMenu += '</div>';

                if (self.is_hr_manager && data._name === 'hr.employee') {
                    $node.append(secondMenuIcon).append(secondMenu);
                }
            }
        });

        self.state.orgchart.init({ 'direction': self.state.direction });

        self.chartContainertRef.el.querySelectorAll(".add_node").forEach(function (elem) {
            elem.addEventListener("click", self._on_add_node.bind(self));
        });

        self.chartContainertRef.el.querySelectorAll(".edit_node").forEach(function (elem) {
            elem.addEventListener("click", self._on_edit_node.bind(self));
        });

        self.chartContainertRef.el.querySelectorAll(".delete_node").forEach(function (elem) {
            elem.addEventListener("click", self._on_delete_node.bind(self));
        });

        self.chartContainertRef.el.querySelectorAll(".node").forEach(function (elem) {
            elem.addEventListener("dragstart", self._on_drag_node.bind(self));
        });

        self.chartContainertRef.el.querySelectorAll(".node").forEach(function (elem) {
            elem.addEventListener("drop", self._on_drop_node.bind(self));
        });

    }
    _onResize() {
        var self = this;
        var width = $(window).width();
        if (width > 576) {
            self.state.orgchart.init({ 'verticalLevel': 10 });
        } else {
            self.state.orgchart.init({ 'verticalLevel': 2 });
        }

        var $container = $(this.chartContainertRef.el);
        if ($container != undefined) {
            $container.scrollLeft(($container && $container[0].scrollWidth - $container.width()) / 2);
        }
    }
    onClickSearch() {
        var self = this;
        self.clearFilterResult();
        self.filterNodes(self.searchInputRef.el.value.toLowerCase());
    }
    onClickClearSearch() {
        var self = this;
        self.clearFilterResult();
    }
    onKeyupSearch(ev) {
        ev.preventDefault();
        var self = this;
        var value = ev.target.value.toLowerCase().trim();

        if (value.length != 0) {
            self.filterNodes(value.toLowerCase());
        } else {
            self.clearFilterResult();
        }
    }
    onClickReload() {
        var self = this;
        $(self.chartContainertRef.el).empty();
        self.fetch_data().then(function () {
            self.render_orgchart();
        });
    }
    // onClickExportPNG() {
    //     var self = this;
    //     var $oContent = $(self.chartContainertRef.el);
    //     $oContent.addClass('chart_export');
    //     self.state.orgchart.export('Employe OrgChart', 'png');
    //     $oContent.removeClass('chart_export');
    //     $oContent.find('.mask').remove();
    // }


    onClickExportPNG() {
        var self = this;
        var $chartContainer = $(self.chartContainertRef.el);
        var $oContent = $chartContainer;

        if (!$chartContainer.length) {
            self.notification.add(_t("Chart container not found."), { type: "danger" });
            return;
        }

        $oContent.addClass('chart_export');

        if ($chartContainer.find('.spinner').length) {
            return;
        }

        var $mask = $chartContainer.find('.mask');
        if (!$mask.length) {
            $chartContainer.append('<div class="mask"><i class="oci oci-spinner spinner"></i></div>');
        } else {
            $mask.removeClass('hidden');
        }

        var sourceChart = $chartContainer.addClass('canvasContainer')
            .find('.orgchart:not(".hidden")')
            .get(0);

        if (!sourceChart) {
            console.error("Org chart element not found.");
            $chartContainer.find('.mask').remove();
            $oContent.removeClass('chart_export');
            return;
        }

        var flag = self.state.orgchart.options.direction === 'l2r' || self.state.orgchart.options.direction === 'r2l';


        html2canvas(sourceChart, {
            scale: 2,  // Higher quality output
            useCORS: true,
            onclone: function (cloneDoc) {
                const $cloneContainer = $(cloneDoc).find('.canvasContainer');
                $cloneContainer.css('overflow', 'visible');
                $cloneContainer.find('.orgchart:not(".hidden")').css('transform', 'none');
                $cloneContainer.find('.second-menu-icon').hide();
            }
        }).then(function (canvas) {
            $chartContainer.find('.mask').remove();
            $oContent.removeClass('chart_export');

            const imgData = canvas.toDataURL('image/png');
            const canvasWidth = canvas.width;
            const canvasHeight = canvas.height;

            // Step 1: Download image as PNG
            const downloadLink = document.createElement('a');
            downloadLink.href = imgData;
            downloadLink.download = 'Employee_OrgChart.png';
            document.body.appendChild(downloadLink);
            downloadLink.click();
        });
    }




    onClickExportPDF() {
        var self = this;
        var $chartContainer = $(self.chartContainertRef.el);
        var $oContent = $chartContainer;

        if (!$chartContainer.length) {
            self.notification.add(_t("Chart container not found."), { type: "danger" });
            return;
        }

        $oContent.addClass('chart_export');

        if ($chartContainer.find('.spinner').length) {
            return;
        }

        var $mask = $chartContainer.find('.mask');
        if (!$mask.length) {
            $chartContainer.append('<div class="mask"><i class="oci oci-spinner spinner"></i></div>');
        } else {
            $mask.removeClass('hidden');
        }

        var sourceChart = $chartContainer.addClass('canvasContainer')
            .find('.orgchart:not(".hidden")')
            .get(0);

        if (!sourceChart) {
            console.error("Org chart element not found.");
            $chartContainer.find('.mask').remove();
            $oContent.removeClass('chart_export');
            return;
        }

        var flag = self.state.orgchart.options.direction === 'l2r' || self.state.orgchart.options.direction === 'r2l';

        // html2canvas(sourceChart, {
        //     width: flag ? sourceChart.clientHeight : sourceChart.clientWidth,
        //     height: flag ? sourceChart.clientWidth : sourceChart.clientHeight,
        //     onclone: function (cloneDoc) {
        //         $(cloneDoc).find('.canvasContainer').css('overflow', 'visible')
        //             .find('.orgchart:not(".hidden"):first').css('transform', '');
        //         $(cloneDoc).find('.second-menu-icon').css('display', 'none');
        //     }
        // }).then(function (canvas) {
        //     try {
        //         $chartContainer.find('.mask').remove();
        //         $oContent.removeClass('chart_export');

        //         var dataUrl = canvas.toDataURL('image/png');
        //         if (!dataUrl.startsWith('data:image/png')) {
        //             self.notification.add(_t("Invalid image data format from canvas."), { type: "danger" });
        //         }

        //         var docWidth = Math.floor(canvas.width);
        //         var docHeight = Math.floor(canvas.height);

        //         if (!window.jsPDF) {
        //             window.jsPDF = window.jspdf.jsPDF;
        //         }

        //         var doc;
        //         if (docWidth > docHeight) {
        //             doc = new jsPDF({
        //                 orientation: 'landscape',
        //                 unit: 'px',
        //                 format: [docWidth, docHeight]
        //             });
        //         } else {
        //             doc = new jsPDF({
        //                 orientation: 'portrait',
        //                 unit: 'px',
        //                 format: [docHeight, docWidth]
        //             });
        //         }

        //         var width = doc.internal.pageSize.getWidth();
        //         var height = doc.internal.pageSize.getHeight();
        //         doc.addImage(dataUrl, 'PNG', 0, 0, width, height);
        //         doc.save('Employee_OrgChart.pdf');

        //     } catch (error) {
        //         console.error("Failed to generate PDF:", error);
        //         self.notification.add(_t("Failed to export the chart as PDF. See console for details."), { type: "danger" });
        //     } finally {
        //         $chartContainer.removeClass('canvasContainer');
        //     }
        // }).catch(function (err) {
        //     console.error("html2canvas error:", err);
        //     self.notification.add(_t("An error occurred while rendering the chart. Please try again."), { type: "danger" });
        //     $chartContainer.removeClass('canvasContainer');
        //     $chartContainer.find('.mask').remove();
        //     $oContent.removeClass('chart_export');
        // });

       

        html2canvas(sourceChart, {
            scale: 2,  // Higher quality output
            useCORS: true,
            onclone: function (cloneDoc) {
                const $cloneContainer = $(cloneDoc).find('.canvasContainer');
                $cloneContainer.css('overflow', 'visible');
                $cloneContainer.find('.orgchart:not(".hidden")').css('transform', 'none');
                $cloneContainer.find('.second-menu-icon').hide();
            }
        }).then(function (canvas) {
            $chartContainer.find('.mask').remove();
            $oContent.removeClass('chart_export');

            const imgData = canvas.toDataURL('image/png');
            const canvasWidth = canvas.width;
            const canvasHeight = canvas.height;

            if (!window.jsPDF) {
                window.jsPDF = window.jspdf.jsPDF;
            }

            const pdf = new jsPDF({
                orientation: canvasWidth > canvasHeight ? 'landscape' : 'portrait',
                unit: 'px',
                format: [canvasWidth, canvasHeight]
            });

            pdf.addImage(imgData, 'PNG', 0, 0, canvasWidth, canvasHeight);
            pdf.save('Employee_OrgChart.pdf');

            $chartContainer.removeClass('canvasContainer');
        })
        .catch(function (err) {
            console.error("html2canvas error:", err);
            self.notification.add(_t("An error occurred while rendering the chart. Please try again."), { type: "danger" });
            $chartContainer.removeClass('canvasContainer');
            $chartContainer.find('.mask').remove();
            $oContent.removeClass('chart_export');
        });

    }
    onClickSwitchChart() {
        var self = this;
        if (self.state.orgchart && self.state.orgchart != undefined) {
            if (self.state.direction == 't2b' && self.state.orgchart.options.direction === "t2b") {
                self.state.direction = 'l2r';
                $(self.chartContainertRef.el).empty();
                $(self.chartContainertRef.el).css('text-align', 'left');
                self.render_orgchart();
            } else if (self.state.direction == 'l2r' && self.state.orgchart.options.direction === "l2r") {
                self.state.direction = 't2b';
                $(self.chartContainertRef.el).empty();
                $(self.chartContainertRef.el).css('text-align', 'center');
                self.render_orgchart();
            }
        }
    }
    onClickSZommIn() {
        var self = this;
        var currentZoom = parseFloat($(self.chartContainertRef.el).css('zoom'));
        $(self.chartContainertRef.el).css('zoom', currentZoom += 0.1);
    }
    onClickSZommOut() {
        var self = this;
        var currentZoom = parseFloat($(self.chartContainertRef.el).css('zoom'));
        $(self.chartContainertRef.el).css('zoom', currentZoom -= 0.1);
    }
    onClickPath() {
        var self = this;
        var $selected = $(self.chartContainertRef.el).find('.node.focused');
        if ($selected.length) {
            $selected.parents('.nodes').children(':has(.focused)').find('.node:first').each(function (index, superior) {
                if (!$(superior).find('.horizontalEdge:first').closest('table').parent().siblings().is('.hidden')) {
                    $(superior).find('.horizontalEdge:first').trigger('click');
                }
            });
        } else {
            alert('please select the node firstly');
        }
    }
    onClickExpand() {
        var self = this;
        $(self.chartContainertRef.el).empty();
        self.fetch_data().then(function () {
            self.render_orgchart();
        }).then(function () {
            self.state.orgchart.$chart.removeClass('noncollapsable')
                .find('.node').removeClass('matched retained')
                .end().find('.hidden, .isChildrenCollapsed, .first-shown, .last-shown').removeClass('hidden isChildrenCollapsed first-shown last-shown')
                .end().find('.slide-up, .slide-left, .slide-right').removeClass('slide-up slide-right slide-left');
        });
    }
    clearFilterResult() {
        var self = this;
        self.state.orgchart.$chart.removeClass('noncollapsable')
            .find('.node').removeClass('matched retained')
            .end().find('.hidden, .isChildrenCollapsed, .first-shown, .last-shown').removeClass('hidden isChildrenCollapsed first-shown last-shown')
            .end().find('.slide-up, .slide-left, .slide-right').removeClass('slide-up slide-right slide-left');
    }
    filterNodes(keyWord) {
        var self = this;
        if (!keyWord.length) {
            window.alert('Please type key word firstly.');
            return;
        } else {
            var $chart = self.state.orgchart.$chart;
            // disalbe the expand/collapse feture
            $chart.addClass('noncollapsable');
            // distinguish the matched nodes and the unmatched nodes according to the given key word
            $chart.find('.node').filter(function (index, node) {
                return $(node).text().toLowerCase().indexOf(keyWord) > -1;
            }).addClass('matched')
                .closest('.hierarchy').parents('.hierarchy').children('.node').addClass('retained');
            // hide the unmatched nodes
            $chart.find('.matched,.retained').each(function (index, node) {
                $(node).removeClass('slide-up')
                    .closest('.nodes').removeClass('hidden')
                    .siblings('.hierarchy').removeClass('isChildrenCollapsed');
                var $unmatched = $(node).closest('.hierarchy').siblings().find('.node:first:not(.matched,.retained)')
                    .closest('.hierarchy').addClass('hidden');
            });
            // hide the redundant descendant nodes of the matched nodes
            $chart.find('.matched').each(function (index, node) {
                if (!$(node).siblings('.nodes').find('.matched').length) {
                    $(node).siblings('.nodes').addClass('hidden')
                        .parent().addClass('isChildrenCollapsed');
                }
            });
            // loop chart and adjust lines
            self.loopChart($chart.find('.hierarchy:first'));
        }
    }

    loopChart($hierarchy) {
        var self = this;
        var $siblings = $hierarchy.children('.nodes').children('.hierarchy');
        if ($siblings.length) {
            $siblings.filter(':not(.hidden)').first().addClass('first-shown')
                .end().last().addClass('last-shown');
        }
        $siblings.each(function (index, sibling) {
            self.loopChart($(sibling));
        });
    }
    _on_add_node(event) {
        event.stopPropagation();
        event.preventDefault();
        var self = this;
        var parent_id = event.target.id;
        if (parent_id) {
            self.dialog.add(FormViewDialog, {
                resModel: 'hr.employee',
                context: {
                    default_parent_id: parseInt(parent_id)
                },
                onRecordSaved: async () => {
                    $(self.chartContainertRef.el).empty();
                    self.fetch_data().then(function () {
                        self.render_orgchart();
                    });
                }
            });
        } else {
            return self.notification.add(
                _t("Something went wrong: Please contact admnistrator."), {
                type: "danger",
            }
            );
        }
    }

    _on_edit_node(event) {
        event.stopPropagation();
        event.preventDefault();
        var self = this;
        var parent_id = event.target.id;
        if (parent_id) {
            self.dialog.add(FormViewDialog, {
                resModel: 'hr.employee',
                resId: parseInt(parent_id),
                context: {},
                onRecordSaved: async () => {
                    $(self.chartContainertRef.el).empty();
                    self.fetch_data().then(function () {
                        self.render_orgchart();
                    });
                }
            });
        }
    }
    _on_delete_node(event) {
        event.stopPropagation();
        event.preventDefault();
        var self = this;
        var employee_id = event.target.id;
        if (employee_id) {
            self.dialog.add(ConfirmationDialog, {
                title: _t("Delete Time Off'"),
                body: _t("This will delete the Time Off. Do you still want to proceed ?"),
                confirm: async () => {
                    const unlink = await self.orm.call('hr.employee', 'unlink', [parseInt(employee_id)]);
                    if (unlink) {
                        $(self.chartContainertRef.el).empty();
                        self.fetch_data().then(function () {
                            self.render_orgchart();
                        });
                    };
                }
            });
        } else {
            return self.notification.add(
                _t("Something went wrong: Please contact admnistrator."), {
                type: "danger",
            }
            );
        }
    }
    _on_drag_node(event) {
        console.log(event)
        event.dataTransfer.setData('source_id', event.target.id);
    }
    _on_drop_node(event) {
        var self = this;
        var source_id = event.dataTransfer.getData("source_id");
        var target_id = event.currentTarget.id;
        if (source_id && target_id) {
            self.rpc('/orgchart/update', {
                source_id: parseInt(source_id),
                target_id: parseInt(target_id),
            }).then(function (result) {
                if (!result) {
                    return self.notification.add(
                        _t("Something went wrong: Please contact admnistrator."), {
                        type: "danger",
                    }
                    );
                }
            });
        } else {
            return self.notification.add(
                _t("Something went wrong: Please contact admnistrator."), {
                type: "danger",
            }
            );
        }
    }
}
EmployeeOrgChart.components = {
    Layout,
}
registry.category("actions").add("organization_chart.employee_orgchart", EmployeeOrgChart);

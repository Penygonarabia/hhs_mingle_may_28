/** @odoo-module **/
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { archParseBoolean } from "@web/views/utils";

export class DomGanttModel extends CalendarModel {
  setup(params, services) {
    super.setup(params, services);
    this.paging = {
      limit: params.eventLimit,
      offset: 0,
      pageCount: 0,
      current: 1,
    };
    this.data = {
      ...this.data,
      planned_date_begin: params?.context?.planned_date_begin || null,
    };
    // console.log(' this.data', this.data)
  }
  get pagingEnable() {
    if (!this.paging.limit) return false;
    return true;
  }
  get records() {
    if (!this.pagingEnable) return this.data.records;
    // Return records which have been rendered to gantt view
    // start index must always from 0
    const fixed_index_start = this.paging.offset;
    const index_start = (this.paging.current - 1) * this.paging.limit;
    const index_end = index_start + this.paging.limit - 1;
    const recordIds = Object.keys(this.data.records);
    const fetchedIds = recordIds.slice(fixed_index_start, index_end);
    const resp = {};
    fetchedIds.forEach((_id) => (resp[_id] = this.data.records[_id]));
    return resp;
  }
  get currentPageRecord() {
    const index_start = (this.paging.current - 1) * this.paging.limit;
    const index_end = index_start + this.paging.limit - 1;
    const recordIds = Object.keys(this.data.records);
    const fetchedIds = recordIds.slice(index_start, index_end);
    const resp = {};
    fetchedIds.forEach((_id) => (resp[_id] = this.data.records[_id]));
    return resp;
  }
  get canCreate() {
    if (this.pagingEnable) return false;
    return this.meta.canCreate && this.data.hasCreateRight;
  }
  get canDelete() {
    if (this.pagingEnable) return false;
    return this.meta.canDelete;
  }
  get canEdit() {
    if (this.pagingEnable) return false;
    if (!this.meta.canEdit) return false;
    return !this.meta.fields[this.meta.fieldMapping.date_start].readonly;
  }
  async updateRecord(record, options = {}) {
    const self = this;
    const rawRecord = this.buildRawRecord(record, options);
    delete rawRecord.name;
    await this.orm
      .write(this.meta.resModel, [record.id], rawRecord, {
        context: { from_ui: true },
      })
      .finally(function () {
        self.load();
      });
  }

  //    Newly added for user_ids maping  12-06-2025
  buildRawRecord(partialRecord, options = {}) {
    const data = super.buildRawRecord(...arguments);
    const fieldNames = Object.keys(this.meta.columnFields);

    // console.log("columnFields:", fieldNames);

    Object.entries(partialRecord).forEach(([fieldName, fieldVal]) => {
      if (
        fieldVal &&
        fieldNames.includes(fieldName) &&
        data[fieldName] === undefined
      ) {
        data[fieldName] = fieldVal;
      }
    });

    // Just assign [resourceId] as an array of integers
    if ("resourceId" in partialRecord) {
      const resourceId = parseInt(partialRecord.resourceId);
      if (!isNaN(resourceId)) {
        data.user_ids = [resourceId]; // Only an array, not (6, 0, [...])
      }
    }

    // console.log("Final data:", data);
    if (this.env?.bus) {
      this.env.bus.trigger("slot-clicked", data);
    }
    return data;
  }

  makeContextDefaults(rawRecord) {
    const context = super.makeContextDefaults(...arguments);
    const fieldNames = Object.keys(this.meta.columnFields);
    // eslint-disable-next-line array-callback-return
    Object.entries(rawRecord).map(([fieldName, fieldVal]) => {
      const defaultKey = `default_${fieldName}`;
      if (fieldNames.includes(fieldName)) {
        if (context[defaultKey] === undefined) {
          context[defaultKey] = fieldVal;
        }
      }
    });
    return context;
  }

  // --------------------------------------------------------------------------

  /**
   * @protected
   * @returns set(start, end)
   */
  computeRange() {
    const { scale, date, firstDayOfWeek } = this.meta;
    let start = date;
    let end = date;

    if (scale !== "week") {
      // StartOf("week") does not depend on locale and will always give the
      // "Monday" of the week...
      start = start.startOf(scale);
      end = end.endOf(scale);
    }

    if (["week"].includes(scale)) {
      const currentWeekOffset = (start.weekday - firstDayOfWeek + 7) % 7;
      start = start.minus({ days: currentWeekOffset });
      end = start.plus({ weeks: scale === "week" ? 1 : 6, days: -1 });
    }

    start = start.startOf("day");
    end = end.endOf("day");

    return { start, end };
  }

  /**
   * @param {Object} data
   * @protected
   * @returns records
   */
  fetchRecords(data) {
    const { fieldNames, resModel } = this.meta;
    const kw = {};
    if (this.meta.resourceOrder) {
      kw.order = this.meta.resourceOrder;
    }
    return this.orm.searchRead(
      resModel,
      this.computeDomain(data),
      fieldNames,
      kw
    );
  }
  /**
   * @protected
   * @param {Object} data
   */
  async updateData(data) {
    await super.updateData(...arguments);
    data.resourceAreaColumns = await this._loadResourceAreaColumns();
    await this._resetPaging();
  }
  async _resetPaging() {
    // This.paging.offset = 0;
    // this.paging.current = 1;
    this.paging.pageCount = 0;

    const recordCount = Object.keys(this.data.records).length;
    if (recordCount > 0) {
      let pageExtra = 0;
      if (recordCount % this.paging.limit > 0) pageExtra = 1;
      this.paging.pageCount =
        parseInt(recordCount / this.paging.limit, 10) + pageExtra;
    }
  }
  async _nextPage() {
    if (!this.paging.pageCount) this._resetPaging();
    if (this.paging.current >= this.paging.pageCount) return false;
    this.paging.current += 1;
    return true;
  }
  async _loadResourceAreaColumns() {
    const fieldNames = Object.keys(this.meta.columnFields).filter(
      (fieldName) => {
        const fieldObject = this.meta.columnFields[fieldName];
        return (
          fieldObject.attrs.is_resource_group_field === undefined &&
          !archParseBoolean(fieldObject.invisible)
        );
      }
    );
    const resp = fieldNames.map((fieldName) => {
      const fieldObject = this.meta.columnFields[fieldName];
      const newItem = {
        field: fieldName,
        headerContent: fieldObject.string,
      };
      if (fieldObject.attrs.gantt_group) {
        newItem.group = true;
      }
      if (fieldObject.attrs.width) {
        newItem.width = fieldObject.attrs.width;
      }
      return newItem;
    });
    return [...resp];
  }
}

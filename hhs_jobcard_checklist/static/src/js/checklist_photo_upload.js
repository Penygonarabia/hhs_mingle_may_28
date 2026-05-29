/** @odoo-module **/

/** @odoo-module **/

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, xml, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ChecklistPhotoUpload extends Component {

    static template = xml`
        <div class="hhs_photo_upload text-center" t-on-click.stop="">

            <!-- Preview -->
            <t t-if="state.preview || props.record.data[props.name]">
                <img t-att-src="state.preview || ('data:image/png;base64,' + props.record.data[props.name])"
                     style="max-width: 100%;
                            max-height: 200px;
                            border-radius: 8px;
                            margin-bottom: 8px;
                            object-fit: contain;"
                     class="img-fluid"/>
            </t>

            <!-- Upload Button -->
            <div class="mt-2">
                <label class="btn btn-outline-primary btn-sm"
                       style="cursor: pointer; padding: 8px 20px; font-size: 0.9rem;"
                       t-on-click.stop="">

                    <i class="fa fa-camera me-1"/> Upload Photo

                    <!--
                        KEY POINTS:
                        - NO capture attribute   → Android shows: Camera / Camera Camcorder / Files
                        - NO accept attribute    → Native picker shows ALL source options
                        This exactly replicates the bottom sheet seen in the screenshot.
                    -->
                    <input type="file"
                           style="display: none;"
                           t-on-change="(ev) => this.onFileChange(ev)"
                           t-on-click.stop=""/>
                </label>
            </div>

        </div>
    `;

    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            preview: null,
        });
    }

    async onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        const isImage = file.type.startsWith("image/");
        const isVideo = file.type.startsWith("video/");

        if (!isImage && !isVideo) {
            console.warn("Unsupported file type:", file.type);
            return;
        }

        const reader = new FileReader();

        reader.onload = async (e) => {
            const base64Full = e.target.result;

            // Show preview for images; placeholder for videos
            if (isImage) {
                this.state.preview = base64Full;
            } else {
                this.state.preview = "/web/static/img/placeholder.png";
            }

            const base64Data = base64Full.split(",")[1];
            const record = this.props.record;

            // Standard OWL record update
            try {
                await record.update({
                    [this.props.name]: base64Data,
                });
            } catch (err) {
                console.warn("Standard update skipped:", err);
            }

            // Direct ORM write for reliability on mobile
            if (record.resId) {
                try {
                    await this.orm.write(
                        "jobcard.checklist.photo",
                        [record.resId],
                        {
                            [this.props.name]: base64Data,
                            photo_filename: file.name,
                        }
                    );
                } catch (err) {
                    console.error("Photo ORM write failed:", err);
                }
            }
        };

        reader.readAsDataURL(file);
    }
}

export const checklistPhotoUpload = {
    component: ChecklistPhotoUpload,
};

registry
    .category("fields")
    .add("checklist_photo_upload", checklistPhotoUpload);

/*import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, xml, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ChecklistPhotoUpload extends Component {
    static template = xml`
        <div class="hhs_photo_upload text-center" t-on-click.stop="">
            <t t-if="state.preview || props.record.data[props.name]">
                <img t-att-src="state.preview || ('data:image/png;base64,' + props.record.data[props.name])"
                     style="max-width: 100%; max-height: 200px; border-radius: 8px; margin-bottom: 8px; object-fit: contain;"
                     class="img-fluid"/>
            </t>
            <div class="mt-2">
                <label class="btn btn-outline-primary btn-sm" 
                       style="cursor: pointer; padding: 8px 20px; font-size: 0.9rem;"
                       t-on-click.stop="">
                    <i class="fa fa-camera me-1"/> Upload Photo
                    <input type="file" 
                           accept="image" 
                           capture="environment"
                           style="display: none;"
                           t-on-change="(ev) => this.onFileChange(ev)"
                           t-on-click.stop=""/>
                </label>
            </div>
        </div>
    `;

    setup() {
        this.orm = useService("orm");
        this.state = useState({ preview: null });
    }

    async onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            const base64Full = e.target.result;
            // Show preview instantly
            this.state.preview = base64Full;

            // Extract pure base64 (remove "data:image/...;base64," prefix)
            const base64Data = base64Full.split(',')[1];

            const record = this.props.record;

            // Try standard update
            try {
                await record.update({ [this.props.name]: base64Data });
            } catch (err) {
                console.log("Standard update blocked for photo");
            }

            // Direct ORM write to guarantee persistence
            if (record.resId) {
                try {
                    await this.orm.write("jobcard.checklist.photo", [record.resId], {
                        [this.props.name]: base64Data,
                    });
                } catch (err) {
                    console.error("Photo ORM write failed:", err);
                }
            }
        };
        reader.readAsDataURL(file);
    }

    static props = { ...standardFieldProps };
}

export const checklistPhotoUpload = { component: ChecklistPhotoUpload };
registry.category("fields").add("checklist_photo_upload", checklistPhotoUpload);
*/

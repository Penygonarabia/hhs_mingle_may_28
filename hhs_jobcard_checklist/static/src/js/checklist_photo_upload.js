/** @odoo-module **/

/** @odoo-module **/

/** @odoo-module **/


//VIJAYA BASKAR WORKING CODE  COMMENTED BY GOKUL ON 2026/06/18 REASON UPLOADED IMAGE PREVIEW NOT SHOWING IN THE JOB CARD
// import { registry } from "@web/core/registry";
// import { standardFieldProps } from "@web/views/fields/standard_field_props";
// import { Component, xml, useState } from "@odoo/owl";
// import { useService } from "@web/core/utils/hooks";
//
// export class ChecklistPhotoUpload extends Component {
//
//     static template = xml`
//         <div class="hhs_photo_upload text-center" t-on-click.stop="">
//
//             <!-- Preview -->
//             <t t-if="state.preview || props.record.data[props.name]">
//                 <img t-att-src="state.preview || ('data:image/png;base64,' + props.record.data[props.name])"
//                      style="max-width: 100%;
//                             max-height: 200px;
//                             border-radius: 8px;
//                             margin-bottom: 8px;
//                             object-fit: contain;"
//                      class="img-fluid"/>
//             </t>
//
//             <!-- Upload Button -->
//             <div class="mt-2">
//                 <label class="btn btn-outline-primary btn-sm"
// 					t-att-style="isReadonly
// 				              ? 'pointer-events:none;opacity:0.6;padding:8px 20px;font-size:0.9rem;'
// 				              : 'cursor:pointer;padding:8px 20px;font-size:0.9rem;'"
//                        t-on-click.stop="">
//
//                     <i class="fa fa-camera me-1"/> Upload Photo
//
//                     <!--
//                         KEY POINTS:
//                         - NO capture attribute   → Android shows: Camera / Camera Camcorder / Files
//                         - NO accept attribute    → Native picker shows ALL source options
//                         This exactly replicates the bottom sheet seen in the screenshot.
//                     -->
//                     <input type="file"
//                            style="display: none;"
//                            t-on-change="(ev) => this.onFileChange(ev)"
// 						   t-att-disabled="isReadonly"
//                            t-on-click.stop=""/>
//                 </label>
//             </div>
//
//         </div>
//     `;
//
//     static props = {
//         ...standardFieldProps,
//     };
//
//     setup() {
//         this.orm = useService("orm");
//         this.state = useState({
//             preview: null,
//         });
//     }
//
// 	get isReadonly() {
// 	     return ["101", "102", "103","104","107","108","109","110","111","154","126"].includes(
// 	        String(this.props.record.data.job_card_state_code || "")
// 	    );
// 	}
//
//     async onFileChange(ev) {
//
// 		if (this.isReadonly) {
// 		        return;
// 		    }
//         const file = ev.target.files[0];
//         if (!file) return;
//
//         const isImage = file.type.startsWith("image/");
//         const isVideo = file.type.startsWith("video/");
//
//         if (!isImage && !isVideo) {
//             console.warn("Unsupported file type:", file.type);
//             return;
//         }
//
//         const reader = new FileReader();
//
//         reader.onload = async (e) => {
//             const base64Full = e.target.result;
//
//             // Show preview for images; placeholder for videos
//             if (isImage) {
//                 this.state.preview = base64Full;
//             } else {
//                 this.state.preview = "/web/static/img/placeholder.png";
//             }
//
//             const base64Data = base64Full.split(",")[1];
//             const record = this.props.record;
//
//             // Standard OWL record update
//             try {
//                 await record.update({
//                     [this.props.name]: base64Data,
//                 });
//             } catch (err) {
//                 console.warn("Standard update skipped:", err);
//             }
//
//             // Direct ORM write for reliability on mobile
//             if (record.resId) {
//                 try {
//                     await this.orm.write(
//                         "jobcard.checklist.photo",
//                         [record.resId],
//                         {
//                             [this.props.name]: base64Data,
//                             photo_filename: file.name,
//                         }
//                     );
//                 } catch (err) {
//                     console.error("Photo ORM write failed:", err);
//                 }
//             }
//         };
//
//         reader.readAsDataURL(file);
//     }
// }
//
// export const checklistPhotoUpload = {
//     component: ChecklistPhotoUpload,
// };
//
// registry
//     .category("fields")
//     .add("checklist_photo_upload", checklistPhotoUpload);

//GOKUL 2026/06/18
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, xml, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ChecklistPhotoUpload extends Component {

    static template = xml`
        <div class="hhs_photo_upload text-center" t-on-click.stop="">

            <!-- Image Preview -->
            <t t-if="imageSrc">
                <img t-att-src="imageSrc"
                     style="
                        width:120px;
                        height:120px;
                        object-fit:cover;
                        border-radius:8px;
                        border:1px solid #ddd;
                        margin-bottom:8px;
                     "
                     class="img-fluid"/>
            </t>

            <!-- Upload Button -->
            <div class="mt-2">
                <label class="btn btn-outline-primary btn-sm"
                       t-att-style="isReadonly
                           ? 'pointer-events:none;opacity:0.6;padding:8px 20px;font-size:0.9rem;'
                           : 'cursor:pointer;padding:8px 20px;font-size:0.9rem;'">

                    <i class="fa fa-camera me-1"/> Upload Photo

                    <input type="file"
                           style="display:none;"
                           t-att-disabled="isReadonly"
                           t-on-change="onFileChange"/>
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

    get isReadonly() {
        return [
            "101", "102", "103", "104",
            "107", "108", "109", "110",
            "111", "154", "126"
        ].includes(
            String(this.props.record.data.job_card_state_code || "")
        );
    }

    get imageSrc() {
        const record = this.props.record;

        // Show newly selected image immediately
        if (this.state.preview) {
            return this.state.preview;
        }

        // Existing saved image
        if (record.resId && record.data[this.props.name]) {
            return `/web/image?model=jobcard.checklist.photo&id=${record.resId}&field=${this.props.name}&unique=${Date.now()}`;
        }

        return null;
    }

    async onFileChange(ev) {
        if (this.isReadonly) {
            return;
        }

        const file = ev.target.files?.[0];
        if (!file) {
            return;
        }

        if (!file.type.startsWith("image/")) {
            alert("Please select an image file.");
            return;
        }

        const reader = new FileReader();

        reader.onload = async (e) => {
            try {
                const dataUrl = e.target.result;
                const base64Data = dataUrl.split(",")[1];

                // Immediate preview
                this.state.preview = dataUrl;

                const record = this.props.record;

                // Update current row
                await record.update({
                    [this.props.name]: base64Data,
                });

                // Persist to database
                if (record.resId) {
                    await this.orm.write(
                        "jobcard.checklist.photo",
                        [record.resId],
                        {
                            [this.props.name]: base64Data,
                            photo_filename: file.name,
                        }
                    );
                }

                // Clear preview so /web/image is used
                setTimeout(() => {
                    this.state.preview = null;
                }, 500);

            } catch (error) {
                console.error("Photo upload failed:", error);
            }
        };

        reader.readAsDataURL(file);
    }
}

export const checklistPhotoUpload = {
    component: ChecklistPhotoUpload,
};

registry.category("fields").add(
    "checklist_photo_upload",
    checklistPhotoUpload
);

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

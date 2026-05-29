/** Inside a custom JS module **/
 
import { registry } from "@web/core/registry";
const { onMounted } = owl;
console.log(".........button") 
export class AutoTriggerJobCard extends Component {
    setup() {
        onMounted(() => {
            setTimeout(() => {
                const btn = document.querySelector(".o_open_job_card_btn");
                if (btn) btn.click();
            }, 300);
        });
    }
}
 
registry.category("fields").add("autotrigger_job_card", AutoTriggerJobCard);
 
/** @odoo-module */

let isTouch = false;

function openPreview(imageUrl) {
    if (!imageUrl || imageUrl.includes("placeholder")) return;

    const overlay = document.createElement("div");
    overlay.style = `
        position: fixed;
        top:0; left:0;
        width:100%; height:100%;
        background: rgba(0,0,0,0.95);
        display:flex;
        align-items:center;
        justify-content:center;
        z-index:9999;
    `;

    const img = document.createElement("img");
    img.src = imageUrl;
    img.style = "max-width:95%; max-height:95%; border-radius:10px;";

    const closeBtn = document.createElement("div");
    closeBtn.innerHTML = "✖";
    closeBtn.style = `
        position:absolute;
        top:15px; right:20px;
        font-size:28px;
        color:white;
        cursor:pointer;
    `;

    closeBtn.onclick = (e) => {
        e.stopPropagation();
        overlay.remove();
    };

    overlay.onclick = () => overlay.remove();

    overlay.appendChild(closeBtn);
    overlay.appendChild(img);

    document.body.appendChild(overlay);
}

// ✅ MOBILE (touch)
document.addEventListener("touchstart", function (ev) {
    isTouch = true;

    // ❌ Ignore edit/delete buttons
    if (
        ev.target.closest(".o_image_control") ||
        ev.target.closest(".fa") ||
        ev.target.closest("button")
    ) return;

    // ✅ Force get image inside container
    const container = ev.target.closest(".o_field_image");
    if (!container) return;

    const img = container.querySelector("img");
    if (!img) return;

    openPreview(img.src);
});

// ✅ DESKTOP (click)
document.addEventListener("click", function (ev) {

    if (isTouch) {
        isTouch = false;
        return;
    }

    if (
        ev.target.closest(".o_image_control") ||
        ev.target.closest(".fa") ||
        ev.target.closest("button")
    ) return;

    const container = ev.target.closest(".o_field_image");
    if (!container) return;

    const img = container.querySelector("img");
    if (!img) return;

    openPreview(img.src);
});



///** @odoo-module */
//
//let isTouch = false;
//
//function openImagePreview(imageUrl) {
//    if (!imageUrl || imageUrl.includes("placeholder")) return;
//
//    const overlay = document.createElement("div");
//    overlay.style = `
//        position: fixed;
//        top: 0;
//        left: 0;
//        width: 100%;
//        height: 100%;
//        background: rgba(0,0,0,0.95);
//        display: flex;
//        align-items: center;
//        justify-content: center;
//        z-index: 9999;
//    `;
//
//    const img = document.createElement("img");
//    img.src = imageUrl;
//    img.style = `
//        max-width: 95%;
//        max-height: 95%;
//        border-radius: 10px;
//    `;
//
//    // ❌ Close button
//    const closeBtn = document.createElement("div");
//    closeBtn.innerHTML = "✖";
//    closeBtn.style = `
//        position: absolute;
//        top: 15px;
//        right: 20px;
//        font-size: 28px;
//        color: white;
//        cursor: pointer;
//        z-index: 10000;
//    `;
//
//    closeBtn.onclick = (e) => {
//        e.stopPropagation();
//        overlay.remove();
//    };
//
//    // Tap/click outside → close
//    overlay.onclick = () => overlay.remove();
//
//    overlay.appendChild(closeBtn);
//    overlay.appendChild(img);
//
//    document.body.appendChild(overlay);
//}
//
//// ✅ Mobile touch
//document.addEventListener("touchstart", function (ev) {
//    isTouch = true;
//
//    if (ev.target.closest(".o_image_control") || ev.target.closest("button")) return;
//
//    const img = ev.target.closest(".o_field_image img");
//    if (!img) return;
//
//    openImagePreview(img.src);
//});
//
//// ✅ Desktop click
//document.addEventListener("click", function (ev) {
//    if (isTouch) {
//        isTouch = false; // prevent double trigger
//        return;
//    }
//
//    if (ev.target.closest(".o_image_control") || ev.target.closest("button")) return;
//
//    const img = ev.target.closest(".o_field_image img");
//    if (!img) return;
//
//    openImagePreview(img.src);
//});
//
//
//
//
//
//
//
//
//
//
/////** @odoo-module */
////
////document.addEventListener("click", function (ev) {
////
////    // ❌ Ignore clicks on buttons/icons (edit/delete)
////    if (
////        ev.target.closest(".o_image_control") ||   // edit/delete buttons
////        ev.target.closest("button") ||
////        ev.target.closest(".fa")                  // icons
////    ) {
////        return;
////    }
////
////    // ✅ Only target actual image inside image field
////    const img = ev.target.closest(".o_field_image img");
////
////    if (!img) return;
////
////    const imageUrl = img.src;
////
////    // Ignore placeholder
////    if (!imageUrl || imageUrl.includes("placeholder")) return;
////
////    const overlay = document.createElement("div");
////    overlay.style = `
////        position: fixed;
////        top: 0;
////        left: 0;
////        width: 100%;
////        height: 100%;
////        background: rgba(0,0,0,0.9);
////        display: flex;
////        align-items: center;
////        justify-content: center;
////        z-index: 9999;
////    `;
////
////    const previewImg = document.createElement("img");
////    previewImg.src = imageUrl;
////    previewImg.style = `
////        max-width: 90%;
////        max-height: 90%;
////        border-radius: 10px;
////    `;
////
////    // ❌ Close Button
////    const closeBtn = document.createElement("div");
////    closeBtn.innerHTML = "✖";
////    closeBtn.style = `
////        position: absolute;
////        top: 20px;
////        right: 30px;
////        font-size: 30px;
////        color: white;
////        cursor: pointer;
////        z-index: 10000;
////    `;
////
////    closeBtn.onclick = (e) => {
////        e.stopPropagation();
////        overlay.remove();
////    };
////
////    overlay.onclick = () => overlay.remove();
////
////    overlay.appendChild(closeBtn);
////    overlay.appendChild(previewImg);
////
////    document.body.appendChild(overlay);
////});

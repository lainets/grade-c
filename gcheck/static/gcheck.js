function gcheck_toggle(e) {
    if(e.className.includes("gcheck-collapsed")) {
        e.className = e.className.replace("gcheck-collapsed", "").trim()
    } else {
        e.className = e.className + " gcheck-collapsed"
    }
}
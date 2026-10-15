document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("verMas");
    const columnasExtra = document.querySelectorAll(".extra-col");

    if (!btn) return; // seguridad

    btn.addEventListener("click", function (e) {
        e.preventDefault();

        columnasExtra.forEach(col => {
            col.classList.toggle("d-none");
        });

        btn.textContent = btn.textContent === "Ver más"
            ? "Ver menos"
            : "Ver más";
    });
});
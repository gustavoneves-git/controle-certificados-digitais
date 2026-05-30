function telefoneValido(valor) {
    return /^\d{8,9}$/.test(valor) && !valor.startsWith("55");
}

document.querySelectorAll("[data-phone-form]").forEach((form) => {
    const input = form.querySelector("[data-phone-input]");
    const button = form.querySelector("[data-save-button]");
    const update = () => {
        const ok = telefoneValido(input.value.trim());
        input.classList.toggle("is-valid", ok);
        input.classList.toggle("is-invalid", input.value.length > 0 && !ok);
        button.disabled = !ok;
    };
    input.addEventListener("input", update);
    update();
});

async function buscarSenha(certId) {
    const response = await fetch(`/certificados/${certId}/senha`, { method: "POST" });
    if (!response.ok) {
        throw new Error("Nao foi possivel buscar a senha.");
    }
    return response.json();
}

document.querySelectorAll("[data-show-password]").forEach((button) => {
    button.addEventListener("click", async () => {
        const output = document.querySelector("[data-password-output]");
        const showing = output.type === "text";
        if (showing) {
            output.type = "password";
            output.value = "********";
            button.textContent = "Mostrar";
            return;
        }
        const data = await buscarSenha(button.dataset.certId);
        output.type = "text";
        output.value = data.senha;
        button.textContent = "Ocultar";
    });
});

document.querySelectorAll("[data-toggle-local-password]").forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.querySelector("[data-local-password]");
        const showing = input.type === "text";
        input.type = showing ? "password" : "text";
        button.textContent = showing ? "Mostrar" : "Ocultar";
    });
});

document.querySelectorAll("[data-copy-password]").forEach((button) => {
    button.addEventListener("click", async () => {
        const data = await buscarSenha(button.dataset.certId);
        await navigator.clipboard.writeText(data.senha);
        await fetch(`/certificados/${button.dataset.certId}/senha/copiar`, { method: "POST" });
        button.textContent = "Copiada";
        setTimeout(() => (button.textContent = "Copiar senha"), 1400);
    });
});

document.querySelectorAll("[data-copy-message]").forEach((button) => {
    button.addEventListener("click", async () => {
        const output = document.querySelector("[data-message-output]");
        await navigator.clipboard.writeText(output.value);
        if (button.dataset.messageId) {
            await fetch(`/mensagens/${button.dataset.messageId}/copiar`, { method: "POST" });
        }
        button.textContent = "Mensagem copiada";
        setTimeout(() => (button.textContent = "Copiar mensagem"), 1400);
    });
});

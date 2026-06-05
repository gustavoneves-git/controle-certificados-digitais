function telefoneValido(valor) {
    if (/[A-Za-z]/.test(valor)) return false;
    const digits = valor.replace(/\D/g, "");
    if (digits.startsWith("55")) return /^\d{12,13}$/.test(digits);
    if (digits.startsWith("1")) return /^\d{11}$/.test(digits);
    return false;
}

function formatarTelefone(valor) {
    const digits = valor.replace(/\D/g, "").slice(0, 15);
    if (digits.length <= 2) return digits ? `+${digits}` : "";
    if (digits.startsWith("1")) {
        if (digits.length <= 4) return `+${digits.slice(0, 1)} ${digits.slice(1)}`;
        if (digits.length <= 7) return `+${digits.slice(0, 1)} ${digits.slice(1, 4)}-${digits.slice(4)}`;
        if (digits.length <= 11) return `+${digits.slice(0, 1)} ${digits.slice(1, 4)}-${digits.slice(4, 7)}-${digits.slice(7)}`;
    }
    if (digits.length <= 4) return `+${digits.slice(0, 2)} ${digits.slice(2)}`;
    if (digits.length <= 8) {
        return `+${digits.slice(0, 2)} ${digits.slice(2, 4)} ${digits.slice(4)}`;
    }
    if (digits.length > 13) {
        return `+${digits}`;
    }
    const phoneStart = digits.length === 13 ? 9 : 8;
    return `+${digits.slice(0, 2)} ${digits.slice(2, 4)} ${digits.slice(4, phoneStart)}-${digits.slice(phoneStart)}`;
}

document.querySelectorAll("[data-phone-form]").forEach((form) => {
    const input = form.querySelector("[data-phone-input]");
    const button = form.querySelector("[data-save-button]");
    const update = () => {
        const valor = input.value.trim();
        const vazio = valor.length === 0;
        const ok = telefoneValido(valor);
        input.classList.toggle("is-valid", ok);
        input.classList.toggle("is-invalid", !vazio && !ok);
        button.disabled = !vazio && !ok;
    };
    input.addEventListener("input", () => {
        input.value = formatarTelefone(input.value);
        update();
    });
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

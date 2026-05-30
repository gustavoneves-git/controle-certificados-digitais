import re

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtensionOID, NameOID


class SenhaCertificadoInvalida(Exception):
    pass


def ler_pfx(conteudo, senha):
    try:
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            conteudo,
            (senha or "").encode("utf-8"),
        )
    except Exception as exc:
        raise SenhaCertificadoInvalida("Senha invalida ou arquivo .pfx ilegivel") from exc

    if certificate is None:
        raise SenhaCertificadoInvalida("Arquivo .pfx sem certificado principal")

    subject = certificate.subject.rfc4514_string()
    issuer = certificate.issuer.rfc4514_string()
    texto_busca = _texto_para_busca(certificate, subject, issuer)
    cnpj_cpf, tipo_documento = extrair_documento(texto_busca)

    return {
        "subject": subject,
        "issuer": issuer,
        "data_emissao": certificate.not_valid_before_utc.date().isoformat(),
        "data_validade": certificate.not_valid_after_utc.date().isoformat(),
        "thumbprint_sha1": certificate.fingerprint(hashes.SHA1()).hex().upper(),
        "thumbprint_sha256": certificate.fingerprint(hashes.SHA256()).hex().upper(),
        "serial_number": str(certificate.serial_number),
        "cnpj_cpf": cnpj_cpf,
        "tipo_documento": tipo_documento,
        "nome_extraido": extrair_nome(certificate),
        "tem_chave_privada": private_key is not None,
        "certificados_adicionais": len(additional_certificates or []),
    }


def extrair_documento(texto):
    grupos = re.findall(r"\d[\d.\-\/\s]{9,}\d", texto or "")
    for grupo in grupos:
        digitos = re.sub(r"\D", "", grupo)
        if len(digitos) == 14:
            return digitos, "CNPJ"
        if len(digitos) == 11:
            return digitos, "CPF"
        if len(digitos) > 14:
            for tamanho, tipo in ((14, "CNPJ"), (11, "CPF")):
                for inicio in range(0, len(digitos) - tamanho + 1):
                    candidato = digitos[inicio : inicio + tamanho]
                    if len(candidato) == tamanho:
                        return candidato, tipo
    return None, "DESCONHECIDO"


def extrair_nome(certificate):
    for oid in (NameOID.COMMON_NAME, NameOID.ORGANIZATION_NAME):
        attrs = certificate.subject.get_attributes_for_oid(oid)
        if attrs:
            valor = attrs[0].value.strip()
            return valor.split(":")[0].strip() or valor
    return None


def _texto_para_busca(certificate, subject, issuer):
    partes = [subject, issuer]
    for attr in certificate.subject:
        partes.append(str(attr.value))
    try:
        san = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
        partes.extend(str(nome.value) for nome in san)
    except x509.ExtensionNotFound:
        pass
    return " ".join(partes)

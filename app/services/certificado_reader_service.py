import re

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtensionOID, NameOID, ObjectIdentifier


TELEPHONE_NUMBER_OID = ObjectIdentifier("2.5.4.20")


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
    cnpj_cpf, tipo_documento = extrair_documento_preferindo_cn(certificate, texto_busca)
    nome_extraido = extrair_nome(certificate)

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
        "nome_extraido": nome_extraido,
        "email_certificado": extrair_email(certificate),
        "telefone_certificado": extrair_telefone(certificate),
        "responsavel_certificado": extrair_responsavel(tipo_documento, nome_extraido),
        "tem_chave_privada": private_key is not None,
        "certificados_adicionais": len(additional_certificates or []),
    }


def extrair_documento(texto):
    grupos = re.findall(r"\d[\d.\-\/\s]{9,}\d", texto or "")
    for grupo in grupos:
        digitos = re.sub(r"\D", "", grupo)
        if len(digitos) == 14:
            return digitos, "e-CNPJ"
        if len(digitos) == 11:
            return digitos, "e-CPF"
        if len(digitos) > 14:
            for tamanho, tipo in ((14, "e-CNPJ"), (11, "e-CPF")):
                for inicio in range(0, len(digitos) - tamanho + 1):
                    candidato = digitos[inicio : inicio + tamanho]
                    if len(candidato) == tamanho:
                        return candidato, tipo
    return None, "DESCONHECIDO"


def extrair_documento_preferindo_cn(certificate, texto_fallback):
    for valor_cn in _valores_subject(certificate, NameOID.COMMON_NAME):
        documento, tipo = extrair_documento(valor_cn)
        if documento:
            return documento, tipo
    return extrair_documento(texto_fallback)


def extrair_nome(certificate):
    for oid in (NameOID.COMMON_NAME, NameOID.ORGANIZATION_NAME):
        attrs = certificate.subject.get_attributes_for_oid(oid)
        if attrs:
            valor = attrs[0].value.strip()
            return valor.split(":")[0].strip() or valor
    return None


def extrair_email(certificate):
    emails = []
    emails.extend(_valores_subject(certificate, NameOID.EMAIL_ADDRESS))
    try:
        san = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
        emails.extend(san.get_values_for_type(x509.RFC822Name))
    except x509.ExtensionNotFound:
        pass

    for email in emails:
        valor = str(email).strip()
        if valor:
            return valor
    return None


def extrair_telefone(certificate):
    telefones = _valores_subject(certificate, TELEPHONE_NUMBER_OID)
    for telefone in telefones:
        digitos = re.sub(r"\D", "", telefone)
        if digitos:
            return digitos
    return None


def extrair_responsavel(tipo_documento, nome_extraido):
    if tipo_documento == "e-CPF" and nome_extraido:
        return nome_extraido
    return None


def _valores_subject(certificate, oid):
    return [
        attr.value.strip()
        for attr in certificate.subject.get_attributes_for_oid(oid)
        if str(attr.value).strip()
    ]


def _texto_para_busca(certificate, subject, issuer):
    partes = []
    for attr in certificate.subject:
        partes.append(str(attr.value))
    partes.extend([subject, issuer])
    try:
        san = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
        partes.extend(str(nome.value) for nome in san)
    except x509.ExtensionNotFound:
        pass
    return " ".join(partes)

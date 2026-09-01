# AES 独立 Golden 适配器。
#
# 职责：调用成熟 Cryptodome AES 原语并适配稳定的 padding/counter 合同。
# 边界：不使用 DUT Driver、Wire Codec、固件常量、TargetClient 或硬件 I/O。
# 依赖：pycryptodomex（Cryptodome.Cipher.AES）和 AES models。

from __future__ import annotations

from Cryptodome.Cipher import AES

from ...drivers.aes import AesConfig, AesDirection, AesEndian, AesKeySize, AesMode, AesPadding


def _pkcs7_pad(payload: bytes) -> bytes:
    amount = 16 - (len(payload) % 16)
    return payload + bytes([amount]) * amount


def _zero_pad(payload: bytes) -> bytes:
    if len(payload) % 16 == 0:
        return payload
    return payload + b"\x00" * (16 - (len(payload) % 16))


def _prepare_plaintext(payload: bytes, config: AesConfig) -> bytes:
    if config.mode is AesMode.CTR or config.padding is AesPadding.NONE:
        if len(payload) % 16 and config.mode is not AesMode.CTR:
            raise ValueError("NONE padding requires a block-aligned payload")
        return payload
    if config.padding is AesPadding.PKCS7:
        return _pkcs7_pad(payload)
    return _zero_pad(payload)


def _remove_padding(payload: bytes, config: AesConfig) -> bytes:
    if config.direction is AesDirection.ENCRYPT or config.padding is AesPadding.NONE:
        return payload
    if config.padding is AesPadding.ZERO:
        return payload.rstrip(b"\x00")
    if not payload or payload[-1] == 0 or payload[-1] > 16:
        raise ValueError("invalid PKCS7 padding from reference ciphertext")
    amount = payload[-1]
    if payload[-amount:] != bytes([amount]) * amount:
        raise ValueError("invalid PKCS7 padding from reference ciphertext")
    return payload[:-amount]


def aes_golden(payload: bytes, key: bytes, iv: bytes | None, config: AesConfig) -> bytes:
    value = bytes(payload)
    key_value = bytes(key)
    iv_value = None if iv is None else bytes(iv)
    if len(key_value) not in (16, 32):
        raise ValueError("AES Golden key must be 16 or 32 bytes")
    if config.mode in (AesMode.CBC, AesMode.CTR) and (iv_value is None or len(iv_value) != 16):
        raise ValueError("CBC/CTR Golden requires a 16-byte IV")
    # Golden 始终处理公共契约定义的 canonical bytes。
    # LITTLE/BIG 只决定 Wrap 如何装配硬件 32-bit word，不能再次改变 AES 数学输入或输出。

    if config.direction is AesDirection.ENCRYPT:
        source = _prepare_plaintext(value, config)
    else:
        source = value
        if config.mode is not AesMode.CTR and len(source) % 16:
            raise ValueError("decrypt ciphertext must be block aligned")

    if config.mode is AesMode.ECB:
        cipher = AES.new(key_value, AES.MODE_ECB)
    elif config.mode is AesMode.CBC:
        cipher = AES.new(key_value, AES.MODE_CBC, iv=iv_value)
    else:
        counter = int(config.ctr_counter).to_bytes(4, "big")
        initial_counter = (iv_value[:12] if iv_value is not None else b"\x00" * 12) + counter
        cipher = AES.new(
            key_value, AES.MODE_CTR, nonce=b"", initial_value=int.from_bytes(initial_counter, "big")
        )
    result = (
        cipher.encrypt(source)
        if config.direction is AesDirection.ENCRYPT
        else cipher.decrypt(source)
    )
    return _remove_padding(result, config)


def nist_vectors() -> tuple[tuple[str, bytes, bytes, bytes | None, AesConfig, bytes], ...]:
    # 返回完整的六种模式/密钥尺寸和双向 NIST KAT 矩阵。
    # 解密节点把 ciphertext 作为 payload、原始 plaintext 作为 expected，
    # 保证 Driver 确实执行 DECRYPT，而不是只对同一适配器做 round-trip。

    key128 = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    key256 = bytes.fromhex("603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4")
    plaintext = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
    iv = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    # SVD defines WORK_IV as 16 bytes and BLOCK_CNT as a separate word.  The
    # last IV word is therefore zero; it must not duplicate the counter.
    ctr_iv = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9fafb00000000")
    vectors: list[tuple[str, bytes, bytes, bytes | None, AesConfig, bytes]] = []
    known_ciphertexts = {
        (AesKeySize.AES128, AesMode.ECB): bytes.fromhex("3ad77bb40d7a3660a89ecaf32466ef97"),
        (AesKeySize.AES128, AesMode.CBC): bytes.fromhex("7649abac8119b246cee98e9b12e9197d"),
        (AesKeySize.AES128, AesMode.CTR): bytes.fromhex("874d6191b620e3261bef6864990db6ce"),
        (AesKeySize.AES256, AesMode.ECB): bytes.fromhex("f3eed1bdb5d2a03c064b5a7e3db181f8"),
        (AesKeySize.AES256, AesMode.CBC): bytes.fromhex("f58c4c04d6e5f1ba779eabfb5f7bfbd6"),
        (AesKeySize.AES256, AesMode.CTR): bytes.fromhex("601ec313775789a5b7a7f504bbf3d228"),
    }
    for key_size, key in ((AesKeySize.AES128, key128), (AesKeySize.AES256, key256)):
        for mode in (AesMode.ECB, AesMode.CBC, AesMode.CTR):
            vector_iv = None if mode is AesMode.ECB else (iv if mode is AesMode.CBC else ctr_iv)
            counter = 0xFCFDFEFF if mode is AesMode.CTR else 0
            encrypt_config = AesConfig(
                AesDirection.ENCRYPT,
                key_size,
                mode,
                endian=AesEndian.BIG,
                ctr_counter=counter,
            )
            ciphertext = known_ciphertexts[(key_size, mode)]
            vectors.append(
                (
                    f"{mode.name.lower()}{key_size.name[3:]}_encrypt",
                    key,
                    plaintext,
                    vector_iv,
                    encrypt_config,
                    ciphertext,
                )
            )
            decrypt_config = AesConfig(
                AesDirection.DECRYPT,
                key_size,
                mode,
                endian=AesEndian.BIG,
                ctr_counter=counter,
            )
            vectors.append(
                (
                    f"{mode.name.lower()}{key_size.name[3:]}_decrypt",
                    key,
                    ciphertext,
                    vector_iv,
                    decrypt_config,
                    plaintext,
                )
            )
    return tuple(vectors)

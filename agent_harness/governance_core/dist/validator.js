const ID_PATTERN = /^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$/;
const VERSION_PATTERN = /^\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?$/;
function hasDuplicates(values) {
    return new Set(values).size !== values.length;
}
function sameContract(left, right) {
    return (left.id === right.id &&
        left.version === right.version &&
        left.summary === right.summary &&
        left.criticality === right.criticality &&
        left.inputSchema === right.inputSchema &&
        left.outputSchema === right.outputSchema);
}
function validateContract(contract) {
    const reasons = [];
    if (!ID_PATTERN.test(contract.id))
        reasons.push(`非法能力 ID: ${contract.id}`);
    if (!VERSION_PATTERN.test(contract.version))
        reasons.push(`非法能力版本: ${contract.version}`);
    if (!contract.summary.trim())
        reasons.push(`能力 ${contract.id} 缺少摘要`);
    return reasons;
}
export function validateGovernanceManifest(manifest, knownCapabilities) {
    const reasons = [];
    if (manifest.manifestVersion !== '0.1') {
        reasons.push(`不支持的治理清单版本: ${manifest.manifestVersion}`);
    }
    if (!ID_PATTERN.test(manifest.pluginId))
        reasons.push(`非法插件 ID: ${manifest.pluginId}`);
    if (!VERSION_PATTERN.test(manifest.pluginVersion)) {
        reasons.push(`非法插件版本: ${manifest.pluginVersion}`);
    }
    if (!manifest.displayName.trim())
        reasons.push('插件显示名称不能为空');
    if (manifest.scope.kind !== 'global' && !manifest.scope.id?.trim()) {
        reasons.push(`${manifest.scope.kind} 作用域必须提供 scope.id`);
    }
    if (hasDuplicates(manifest.permissions))
        reasons.push('权限声明存在重复项');
    for (const permission of manifest.permissions) {
        if (!ID_PATTERN.test(permission))
            reasons.push(`非法权限 ID: ${permission}`);
    }
    const providedIds = manifest.provides.map(item => item.capability);
    if (hasDuplicates(providedIds))
        reasons.push('能力声明存在重复项');
    for (const declaration of manifest.provides) {
        if (!ID_PATTERN.test(declaration.capability)) {
            reasons.push(`非法能力 ID: ${declaration.capability}`);
            continue;
        }
        const known = knownCapabilities.get(declaration.capability);
        if (known) {
            if (declaration.contract && !sameContract(declaration.contract, known)) {
                reasons.push(`能力 ${declaration.capability} 已存在，禁止静默重定义其契约语义`);
            }
            continue;
        }
        if (!declaration.contract) {
            reasons.push(`未知能力 ${declaration.capability} 必须携带能力契约`);
            continue;
        }
        if (declaration.contract.id !== declaration.capability) {
            reasons.push(`能力声明 ${declaration.capability} 与契约 ID ${declaration.contract.id} 不一致`);
        }
        reasons.push(...validateContract(declaration.contract));
    }
    return {
        status: reasons.length === 0 ? 'admitted' : 'rejected',
        reasons,
    };
}

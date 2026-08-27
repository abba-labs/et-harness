export const CORE_GOVERNANCE_CAPABILITIES = [
    {
        id: 'governance.project',
        version: '0.1',
        summary: '项目身份、项目范围和项目治理入口',
        criticality: 'core',
    },
    {
        id: 'rule.resolve',
        version: '0.1',
        summary: '根据任务范围解析适用规则',
        criticality: 'core',
    },
    {
        id: 'memory.context',
        version: '0.1',
        summary: '根据任务检索相关上下文与历史状态',
        criticality: 'core',
    },
    {
        id: 'test.resolve',
        version: '0.1',
        summary: '根据任务和改动解析所需测试',
        criticality: 'core',
    },
    {
        id: 'evidence.record',
        version: '0.1',
        summary: '记录验证证据并返回稳定引用',
        criticality: 'core',
    },
    {
        id: 'state.read',
        version: '0.1',
        summary: '读取当前治理状态',
        criticality: 'core',
    },
    {
        id: 'state.update',
        version: '0.1',
        summary: '按治理规则更新当前状态',
        criticality: 'core',
    },
];

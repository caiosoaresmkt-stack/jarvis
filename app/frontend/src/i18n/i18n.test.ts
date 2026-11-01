import { describe, expect, it } from 'vitest';
import { translate } from './index';

describe('i18n pt-BR', () => {
  it('traduz textos exatos', () => {
    expect(translate('Settings')).toBe('Configurações');
    expect(translate('  Cancel  ')).toBe('Cancelar');
  });
  it('traduz padrões com {} preservando os valores', () => {
    expect(translate('Agent "Foo" created')).toBe('Agente "Foo" criado');
    expect(translate('Connect 3 sources')).toBe('Conectar 3 fontes');
  });
  it('usa referências numeradas {n}', () => {
    expect(translate('Connected 2 sources: Gmail, Slack.')).toBe(
      '2 fontes conectadas: Gmail, Slack.',
    );
  });
  it('não altera o que não conhece', () => {
    expect(translate('Qual é a capital do Brasil?')).toBeNull();
    expect(translate('mock-pt')).toBeNull();
  });
});

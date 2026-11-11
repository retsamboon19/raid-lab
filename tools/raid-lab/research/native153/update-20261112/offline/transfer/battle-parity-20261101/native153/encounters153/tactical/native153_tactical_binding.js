// Current153 declaration/prefix guards. Call before any listener hooks these entries.
function kraken153Binding() {
  const value = globalThis.NATIVE153_TACTICAL_BINDING;
  if (globalThis.NATIVE153_TACTICAL_BINDING_SHA256 !== '4a7be55f0c5c33d92342f461783cf692949a87e9fc016c6d8b6c30b6a55ba558' ||
      !value || value.clientSha256 !== 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2')
    throw Error('Exact current153 tactical binding is required');
  return value;
}
function requireKraken153Method(method, expectedRva) {
  const rows = Object.values(kraken153Binding().methods).filter(row => row.rva === expectedRva &&
    row.className === method.class.type.name && row.name === method.name);
  if (rows.length !== 1) throw Error('Unbound current153 tactical method: ' + method.name);
  const row = rows[0], game = Process.getModuleByName('GameAssembly.dll');
  if (!method.virtualAddress.equals(game.base.add(row.rva)) || method.returnType.name !== row.returns ||
      method.isStatic !== row.static || method.parameters.length !== row.parameters.length ||
      method.parameters.some((p, i) => p.type.name !== row.parameters[i]))
    throw Error('Current153 tactical signature changed: ' + row.className + '.' + row.name);
  const bytes = new Uint8Array(method.virtualAddress.readByteArray(row.prefixHex.length / 2));
  if (Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('') !== row.prefixHex)
    throw Error('Current153 tactical entry bytes changed: ' + row.className + '.' + row.name);
  return method;
}
function requireKraken153Field(klass, name, expectedOffset) {
  const spec = kraken153Binding().classes[klass.type.name];
  const row = spec && spec.fields.find(value => value.name === name);
  const field = klass.field(name);
  if (!row || field.offset !== row.offset || field.type.name !== row.type ||
      field.isStatic !== Boolean(row.flags & 16) ||
      expectedOffset !== undefined && expectedOffset !== row.offset)
    throw Error('Current153 tactical field changed: ' + klass.type.name + '.' + name);
  return field;
}
function requireKraken153Enum(klass, name, actual) {
  const spec = kraken153Binding().classes[klass.type.name];
  const row = spec && spec.fields.find(value => value.name === name);
  if (!row || !(row.flags & 64) || !Number.isSafeInteger(actual) ||
      Object.prototype.hasOwnProperty.call(row, 'literalValue') && row.literalValue !== actual)
    throw Error('Current153 tactical enum changed: ' + klass.type.name + '.' + name);
  return actual;
}

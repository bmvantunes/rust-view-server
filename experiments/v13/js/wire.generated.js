/*eslint-disable block-scoped-var, id-length, no-control-regex, no-magic-numbers, no-mixed-operators, no-prototype-builtins, no-redeclare, no-shadow, no-var, sort-vars, default-case, jsdoc/require-param*/
import $protobuf from "protobufjs/minimal.js";

// Common aliases
const $Reader = $protobuf.Reader, $Writer = $protobuf.Writer, $util = $protobuf.util;
const $Object = $util.global.Object, $undefined = $util.global.undefined, $Error = $util.global.Error, $RangeError = $util.global.RangeError;

// Exported root namespace
const $root = $protobuf.roots["default"] || ($protobuf.roots["default"] = {});

export const viewwire = $root.viewwire = (() => {

    /**
     * Namespace viewwire.
     * @exports viewwire
     * @namespace
     */
    const viewwire = {};

    viewwire.Value = (function() {

        /**
         * Properties of a Value.
         * @typedef {Object} viewwire.Value.$Properties
         * @property {boolean|null} [nil] Value nil
         * @property {boolean|null} [boolean] Value boolean
         * @property {number|Long|null} [integer] Value integer
         * @property {string|null} [text] Value text
         * @property {Uint8Array|null} [binary] Value binary
         * @property {viewwire.Sequence.$Properties|null} [sequence] Value sequence
         * @property {viewwire.Object.$Properties|null} [object] Value object
         * @property {Uint8Array|null} [exact] Value exact
         * @property {"nil"|"boolean"|"integer"|"text"|"binary"|"sequence"|"object"|"exact"} [value] Value value
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */

        /**
         * Properties of a Value.
         * @memberof viewwire
         * @interface IValue
         * @augments viewwire.Value.$Properties
         * @deprecated Use viewwire.Value.$Properties instead.
         */

        /**
         * Narrowed shape of a Value.
         * @typedef {{
         *   nil?: boolean|null;
         *   boolean?: boolean|null;
         *   integer?: number|Long|null;
         *   text?: string|null;
         *   binary?: Uint8Array|null;
         *   sequence?: viewwire.Sequence.$Shape|null;
         *   object?: viewwire.Object.$Shape|null;
         *   exact?: Uint8Array|null;
         *   $unknowns?: Array.<Uint8Array>;
         * } & (
         *   ({ value?: undefined; nil?: null; boolean?: null; integer?: null; text?: null; binary?: null; sequence?: null; object?: null; exact?: null }|{ value?: "nil"; nil: boolean; boolean?: null; integer?: null; text?: null; binary?: null; sequence?: null; object?: null; exact?: null }|{ value?: "boolean"; nil?: null; boolean: boolean; integer?: null; text?: null; binary?: null; sequence?: null; object?: null; exact?: null }|{ value?: "integer"; nil?: null; boolean?: null; integer: number|Long; text?: null; binary?: null; sequence?: null; object?: null; exact?: null }|{ value?: "text"; nil?: null; boolean?: null; integer?: null; text: string; binary?: null; sequence?: null; object?: null; exact?: null }|{ value?: "binary"; nil?: null; boolean?: null; integer?: null; text?: null; binary: Uint8Array; sequence?: null; object?: null; exact?: null }|{ value?: "sequence"; nil?: null; boolean?: null; integer?: null; text?: null; binary?: null; sequence: viewwire.Sequence.$Shape; object?: null; exact?: null }|{ value?: "object"; nil?: null; boolean?: null; integer?: null; text?: null; binary?: null; sequence?: null; object: viewwire.Object.$Shape; exact?: null }|{ value?: "exact"; nil?: null; boolean?: null; integer?: null; text?: null; binary?: null; sequence?: null; object?: null; exact: Uint8Array })
         * )} viewwire.Value.$Shape
         */

        /**
         * Constructs a new Value.
         * @memberof viewwire
         * @classdesc Represents a Value.
         * @constructor
         * @param {viewwire.Value.$Properties=} [properties] Properties to set
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */
        const Value = function (properties) {
            if (properties)
                for (let keys = $Object.keys(properties), i = 0; i < keys.length; ++i)
                    if (properties[keys[i]] != null && keys[i] !== "__proto__")
                        this[keys[i]] = properties[keys[i]];
        };

        /**
         * Value nil.
         * @member {boolean|null|undefined} nil
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.nil = null;

        /**
         * Value boolean.
         * @member {boolean|null|undefined} boolean
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.boolean = null;

        /**
         * Value integer.
         * @member {number|Long|null|undefined} integer
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.integer = null;

        /**
         * Value text.
         * @member {string|null|undefined} text
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.text = null;

        /**
         * Value binary.
         * @member {Uint8Array|null|undefined} binary
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.binary = null;

        /**
         * Value sequence.
         * @member {viewwire.Sequence.$Properties|null|undefined} sequence
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.sequence = null;

        /**
         * Value object.
         * @member {viewwire.Object.$Properties|null|undefined} object
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.object = null;

        /**
         * Value exact.
         * @member {Uint8Array|null|undefined} exact
         * @memberof viewwire.Value
         * @instance
         */
        Value.prototype.exact = null;

        // OneOf field names bound to virtual getters and setters
        let $oneOfFields;

        /**
         * Value value.
         * @member {"nil"|"boolean"|"integer"|"text"|"binary"|"sequence"|"object"|"exact"|undefined} value
         * @memberof viewwire.Value
         * @instance
         */
        $Object.defineProperty(Value.prototype, "value", {
            get: $util.oneOfGetter($oneOfFields = ["nil", "boolean", "integer", "text", "binary", "sequence", "object", "exact"]),
            set: $util.oneOfSetter($oneOfFields)
        });

        /**
         * Encodes the specified Value message. Does not implicitly {@link viewwire.Value.verify|verify} messages.
         * @function encode
         * @memberof viewwire.Value
         * @static
         * @param {viewwire.Value.$Properties} message Value message or plain object to encode
         * @param {$protobuf.Writer} [writer] Writer to encode to
         * @returns {$protobuf.Writer} Writer
         */
        Value.encode = function (message, writer, _depth) {
            if (!writer)
                writer = $Writer.create();
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $util.recursionLimit)
                throw $Error("max depth exceeded");
            if (message.nil != null && $Object.hasOwnProperty.call(message, "nil"))
                writer.uint32(/* id 1, wireType 0 =*/8).bool(message.nil);
            if (message.boolean != null && $Object.hasOwnProperty.call(message, "boolean"))
                writer.uint32(/* id 2, wireType 0 =*/16).bool(message.boolean);
            if (message.integer != null && $Object.hasOwnProperty.call(message, "integer"))
                writer.uint32(/* id 3, wireType 0 =*/24).sint64(message.integer);
            if (message.text != null && $Object.hasOwnProperty.call(message, "text"))
                writer.uint32(/* id 4, wireType 2 =*/34).string(message.text);
            if (message.binary != null && $Object.hasOwnProperty.call(message, "binary"))
                writer.uint32(/* id 5, wireType 2 =*/42).bytes(message.binary);
            if (message.sequence != null && $Object.hasOwnProperty.call(message, "sequence"))
                $root.viewwire.Sequence.encode(message.sequence, writer.uint32(/* id 6, wireType 2 =*/50).fork(), _depth + 1).ldelim();
            if (message.object != null && $Object.hasOwnProperty.call(message, "object"))
                $root.viewwire.Object.encode(message.object, writer.uint32(/* id 7, wireType 2 =*/58).fork(), _depth + 1).ldelim();
            if (message.exact != null && $Object.hasOwnProperty.call(message, "exact"))
                writer.uint32(/* id 8, wireType 2 =*/66).bytes(message.exact);
            if (message.$unknowns != null && $Object.hasOwnProperty.call(message, "$unknowns"))
                for (let i = 0; i < message.$unknowns.length; ++i)
                    writer.raw(message.$unknowns[i]);
            return writer;
        };

        /**
         * Decodes a Value message from the specified reader or buffer.
         * @function decode
         * @memberof viewwire.Value
         * @static
         * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
         * @param {number} [length] Message length if known beforehand
         * @returns {viewwire.Value & viewwire.Value.$Shape} Value
         * @throws {Error} If the payload is not a reader or valid buffer
         * @throws {$protobuf.util.ProtocolError} If required fields are missing
         */
        Value.decode = function (reader, length, _end, _depth, _target) {
            if (!(reader instanceof $Reader))
                reader = $Reader.create(reader);
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $Reader.recursionLimit)
                throw $Error("max depth exceeded");
            let end, message;
            if (length === $undefined)
                end = reader.len;
            else {
                end = reader.pos + length;
                if (end > reader.len)
                    throw $RangeError("index out of range");
                length = reader.len;
                reader.len = end;
            }
            message = _target || new $root.viewwire.Value();
            while (reader.pos < end) {
                let start = reader.pos;
                let tag = reader.tag();
                if (tag === _end) {
                    _end = $undefined;
                    break;
                }
                let wireType = tag & 7;
                switch (tag >>>= 3) {
                case 1: {
                        if (wireType !== 0)
                            break;
                        message.nil = reader.bool();
                        message.value = "nil";
                        continue;
                    }
                case 2: {
                        if (wireType !== 0)
                            break;
                        message.boolean = reader.bool();
                        message.value = "boolean";
                        continue;
                    }
                case 3: {
                        if (wireType !== 0)
                            break;
                        message.integer = reader.sint64();
                        message.value = "integer";
                        continue;
                    }
                case 4: {
                        if (wireType !== 2)
                            break;
                        message.text = reader.stringVerify();
                        message.value = "text";
                        continue;
                    }
                case 5: {
                        if (wireType !== 2)
                            break;
                        message.binary = reader.bytes();
                        message.value = "binary";
                        continue;
                    }
                case 6: {
                        if (wireType !== 2)
                            break;
                        message.sequence = $root.viewwire.Sequence.decode(reader, reader.uint32(), $undefined, _depth + 1, message.sequence);
                        message.value = "sequence";
                        continue;
                    }
                case 7: {
                        if (wireType !== 2)
                            break;
                        message.object = $root.viewwire.Object.decode(reader, reader.uint32(), $undefined, _depth + 1, message.object);
                        message.value = "object";
                        continue;
                    }
                case 8: {
                        if (wireType !== 2)
                            break;
                        message.exact = reader.bytes();
                        message.value = "exact";
                        continue;
                    }
                }
                reader.skipType(wireType, _depth, tag);
                if (!reader.discardUnknown) {
                    $util.makeProp(message, "$unknowns", false);
                    (message.$unknowns || (message.$unknowns = [])).push(reader.raw(start, reader.pos));
                }
            }
            if (length !== $undefined) {
                if (reader.pos !== end)
                    throw $RangeError("index out of range");
                reader.len = length;
            }
            if (_end !== $undefined)
                throw $Error("missing end group");
            return message;
        };

        /**
         * Gets the type url for Value
         * @function getTypeUrl
         * @memberof viewwire.Value
         * @static
         * @param {string} [prefix] Custom type url prefix, defaults to `"type.googleapis.com"`
         * @returns {string} The type url
         */
        Value.getTypeUrl = function(prefix) {
            if (prefix === $undefined)
                prefix = "type.googleapis.com";
            return prefix + "/viewwire.Value";
        };

        return Value;
    })();

    viewwire.Sequence = (function() {

        /**
         * Properties of a Sequence.
         * @typedef {Object} viewwire.Sequence.$Properties
         * @property {Array.<viewwire.Value.$Properties>|null} [items] Sequence items
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */

        /**
         * Properties of a Sequence.
         * @memberof viewwire
         * @interface ISequence
         * @augments viewwire.Sequence.$Properties
         * @deprecated Use viewwire.Sequence.$Properties instead.
         */

        /**
         * Shape of a Sequence.
         * @typedef {{
         *   items?: Array.<viewwire.Value.$Shape>|null;
         *   $unknowns?: Array.<Uint8Array>;
         * }} viewwire.Sequence.$Shape
         */

        /**
         * Constructs a new Sequence.
         * @memberof viewwire
         * @classdesc Represents a Sequence.
         * @constructor
         * @param {viewwire.Sequence.$Properties=} [properties] Properties to set
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */
        const Sequence = function (properties) {
            this.items = [];
            if (properties)
                for (let keys = $Object.keys(properties), i = 0; i < keys.length; ++i)
                    if (properties[keys[i]] != null && keys[i] !== "__proto__")
                        this[keys[i]] = properties[keys[i]];
        };

        /**
         * Sequence items.
         * @member {Array.<viewwire.Value.$Properties>} items
         * @memberof viewwire.Sequence
         * @instance
         */
        Sequence.prototype.items = $util.emptyArray;

        /**
         * Encodes the specified Sequence message. Does not implicitly {@link viewwire.Sequence.verify|verify} messages.
         * @function encode
         * @memberof viewwire.Sequence
         * @static
         * @param {viewwire.Sequence.$Properties} message Sequence message or plain object to encode
         * @param {$protobuf.Writer} [writer] Writer to encode to
         * @returns {$protobuf.Writer} Writer
         */
        Sequence.encode = function (message, writer, _depth) {
            if (!writer)
                writer = $Writer.create();
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $util.recursionLimit)
                throw $Error("max depth exceeded");
            if (message.items != null && message.items.length)
                for (let i = 0; i < message.items.length; ++i)
                    $root.viewwire.Value.encode(message.items[i], writer.uint32(/* id 1, wireType 2 =*/10).fork(), _depth + 1).ldelim();
            if (message.$unknowns != null && $Object.hasOwnProperty.call(message, "$unknowns"))
                for (let i = 0; i < message.$unknowns.length; ++i)
                    writer.raw(message.$unknowns[i]);
            return writer;
        };

        /**
         * Decodes a Sequence message from the specified reader or buffer.
         * @function decode
         * @memberof viewwire.Sequence
         * @static
         * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
         * @param {number} [length] Message length if known beforehand
         * @returns {viewwire.Sequence & viewwire.Sequence.$Shape} Sequence
         * @throws {Error} If the payload is not a reader or valid buffer
         * @throws {$protobuf.util.ProtocolError} If required fields are missing
         */
        Sequence.decode = function (reader, length, _end, _depth, _target) {
            if (!(reader instanceof $Reader))
                reader = $Reader.create(reader);
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $Reader.recursionLimit)
                throw $Error("max depth exceeded");
            let end, message;
            if (length === $undefined)
                end = reader.len;
            else {
                end = reader.pos + length;
                if (end > reader.len)
                    throw $RangeError("index out of range");
                length = reader.len;
                reader.len = end;
            }
            message = _target || new $root.viewwire.Sequence();
            while (reader.pos < end) {
                let start = reader.pos;
                let tag = reader.tag();
                if (tag === _end) {
                    _end = $undefined;
                    break;
                }
                let wireType = tag & 7;
                switch (tag >>>= 3) {
                case 1: {
                        if (wireType !== 2)
                            break;
                        if (!(message.items && message.items.length))
                            message.items = [];
                        message.items.push($root.viewwire.Value.decode(reader, reader.uint32(), $undefined, _depth + 1));
                        continue;
                    }
                }
                reader.skipType(wireType, _depth, tag);
                if (!reader.discardUnknown) {
                    $util.makeProp(message, "$unknowns", false);
                    (message.$unknowns || (message.$unknowns = [])).push(reader.raw(start, reader.pos));
                }
            }
            if (length !== $undefined) {
                if (reader.pos !== end)
                    throw $RangeError("index out of range");
                reader.len = length;
            }
            if (_end !== $undefined)
                throw $Error("missing end group");
            return message;
        };

        /**
         * Gets the type url for Sequence
         * @function getTypeUrl
         * @memberof viewwire.Sequence
         * @static
         * @param {string} [prefix] Custom type url prefix, defaults to `"type.googleapis.com"`
         * @returns {string} The type url
         */
        Sequence.getTypeUrl = function(prefix) {
            if (prefix === $undefined)
                prefix = "type.googleapis.com";
            return prefix + "/viewwire.Sequence";
        };

        return Sequence;
    })();

    viewwire.Entry = (function() {

        /**
         * Properties of an Entry.
         * @typedef {Object} viewwire.Entry.$Properties
         * @property {string|null} [key] Entry key
         * @property {viewwire.Value.$Properties|null} [value] Entry value
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */

        /**
         * Properties of an Entry.
         * @memberof viewwire
         * @interface IEntry
         * @augments viewwire.Entry.$Properties
         * @deprecated Use viewwire.Entry.$Properties instead.
         */

        /**
         * Shape of an Entry.
         * @typedef {{
         *   key?: string|null;
         *   value?: viewwire.Value.$Shape|null;
         *   $unknowns?: Array.<Uint8Array>;
         * }} viewwire.Entry.$Shape
         */

        /**
         * Constructs a new Entry.
         * @memberof viewwire
         * @classdesc Represents an Entry.
         * @constructor
         * @param {viewwire.Entry.$Properties=} [properties] Properties to set
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */
        const Entry = function (properties) {
            if (properties)
                for (let keys = $Object.keys(properties), i = 0; i < keys.length; ++i)
                    if (properties[keys[i]] != null && keys[i] !== "__proto__")
                        this[keys[i]] = properties[keys[i]];
        };

        /**
         * Entry key.
         * @member {string} key
         * @memberof viewwire.Entry
         * @instance
         */
        Entry.prototype.key = "";

        /**
         * Entry value.
         * @member {viewwire.Value.$Properties|null|undefined} value
         * @memberof viewwire.Entry
         * @instance
         */
        Entry.prototype.value = null;

        /**
         * Encodes the specified Entry message. Does not implicitly {@link viewwire.Entry.verify|verify} messages.
         * @function encode
         * @memberof viewwire.Entry
         * @static
         * @param {viewwire.Entry.$Properties} message Entry message or plain object to encode
         * @param {$protobuf.Writer} [writer] Writer to encode to
         * @returns {$protobuf.Writer} Writer
         */
        Entry.encode = function (message, writer, _depth) {
            if (!writer)
                writer = $Writer.create();
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $util.recursionLimit)
                throw $Error("max depth exceeded");
            if (message.key != null && $Object.hasOwnProperty.call(message, "key") && message.key !== "")
                writer.uint32(/* id 1, wireType 2 =*/10).string(message.key);
            if (message.value != null && $Object.hasOwnProperty.call(message, "value"))
                $root.viewwire.Value.encode(message.value, writer.uint32(/* id 2, wireType 2 =*/18).fork(), _depth + 1).ldelim();
            if (message.$unknowns != null && $Object.hasOwnProperty.call(message, "$unknowns"))
                for (let i = 0; i < message.$unknowns.length; ++i)
                    writer.raw(message.$unknowns[i]);
            return writer;
        };

        /**
         * Decodes an Entry message from the specified reader or buffer.
         * @function decode
         * @memberof viewwire.Entry
         * @static
         * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
         * @param {number} [length] Message length if known beforehand
         * @returns {viewwire.Entry & viewwire.Entry.$Shape} Entry
         * @throws {Error} If the payload is not a reader or valid buffer
         * @throws {$protobuf.util.ProtocolError} If required fields are missing
         */
        Entry.decode = function (reader, length, _end, _depth, _target) {
            if (!(reader instanceof $Reader))
                reader = $Reader.create(reader);
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $Reader.recursionLimit)
                throw $Error("max depth exceeded");
            let end, message, value;
            if (length === $undefined)
                end = reader.len;
            else {
                end = reader.pos + length;
                if (end > reader.len)
                    throw $RangeError("index out of range");
                length = reader.len;
                reader.len = end;
            }
            message = _target || new $root.viewwire.Entry();
            while (reader.pos < end) {
                let start = reader.pos;
                let tag = reader.tag();
                if (tag === _end) {
                    _end = $undefined;
                    break;
                }
                let wireType = tag & 7;
                switch (tag >>>= 3) {
                case 1: {
                        if (wireType !== 2)
                            break;
                        if ((value = reader.stringVerify()).length)
                            message.key = value;
                        else
                            delete message.key;
                        continue;
                    }
                case 2: {
                        if (wireType !== 2)
                            break;
                        message.value = $root.viewwire.Value.decode(reader, reader.uint32(), $undefined, _depth + 1, message.value);
                        continue;
                    }
                }
                reader.skipType(wireType, _depth, tag);
                if (!reader.discardUnknown) {
                    $util.makeProp(message, "$unknowns", false);
                    (message.$unknowns || (message.$unknowns = [])).push(reader.raw(start, reader.pos));
                }
            }
            if (length !== $undefined) {
                if (reader.pos !== end)
                    throw $RangeError("index out of range");
                reader.len = length;
            }
            if (_end !== $undefined)
                throw $Error("missing end group");
            return message;
        };

        /**
         * Gets the type url for Entry
         * @function getTypeUrl
         * @memberof viewwire.Entry
         * @static
         * @param {string} [prefix] Custom type url prefix, defaults to `"type.googleapis.com"`
         * @returns {string} The type url
         */
        Entry.getTypeUrl = function(prefix) {
            if (prefix === $undefined)
                prefix = "type.googleapis.com";
            return prefix + "/viewwire.Entry";
        };

        return Entry;
    })();

    viewwire.Object = (function() {

        /**
         * Properties of an Object.
         * @typedef {Object} viewwire.Object.$Properties
         * @property {Array.<viewwire.Entry.$Properties>|null} [entries] Object entries
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */

        /**
         * Properties of an Object.
         * @memberof viewwire
         * @interface IObject
         * @augments viewwire.Object.$Properties
         * @deprecated Use viewwire.Object.$Properties instead.
         */

        /**
         * Shape of an Object.
         * @typedef {{
         *   entries?: Array.<viewwire.Entry.$Shape>|null;
         *   $unknowns?: Array.<Uint8Array>;
         * }} viewwire.Object.$Shape
         */

        /**
         * Constructs a new Object.
         * @memberof viewwire
         * @classdesc Represents an Object.
         * @constructor
         * @param {viewwire.Object.$Properties=} [properties] Properties to set
         * @property {Array.<Uint8Array>} [$unknowns] Unknown fields preserved while decoding when enabled
         */
        const Object = function (properties) {
            this.entries = [];
            if (properties)
                for (let keys = $Object.keys(properties), i = 0; i < keys.length; ++i)
                    if (properties[keys[i]] != null && keys[i] !== "__proto__")
                        this[keys[i]] = properties[keys[i]];
        };

        /**
         * Object entries.
         * @member {Array.<viewwire.Entry.$Properties>} entries
         * @memberof viewwire.Object
         * @instance
         */
        Object.prototype.entries = $util.emptyArray;

        /**
         * Encodes the specified Object message. Does not implicitly {@link viewwire.Object.verify|verify} messages.
         * @function encode
         * @memberof viewwire.Object
         * @static
         * @param {viewwire.Object.$Properties} message Object message or plain object to encode
         * @param {$protobuf.Writer} [writer] Writer to encode to
         * @returns {$protobuf.Writer} Writer
         */
        Object.encode = function (message, writer, _depth) {
            if (!writer)
                writer = $Writer.create();
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $util.recursionLimit)
                throw $Error("max depth exceeded");
            if (message.entries != null && message.entries.length)
                for (let i = 0; i < message.entries.length; ++i)
                    $root.viewwire.Entry.encode(message.entries[i], writer.uint32(/* id 1, wireType 2 =*/10).fork(), _depth + 1).ldelim();
            if (message.$unknowns != null && $Object.hasOwnProperty.call(message, "$unknowns"))
                for (let i = 0; i < message.$unknowns.length; ++i)
                    writer.raw(message.$unknowns[i]);
            return writer;
        };

        /**
         * Decodes an Object message from the specified reader or buffer.
         * @function decode
         * @memberof viewwire.Object
         * @static
         * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
         * @param {number} [length] Message length if known beforehand
         * @returns {viewwire.Object & viewwire.Object.$Shape} Object
         * @throws {Error} If the payload is not a reader or valid buffer
         * @throws {$protobuf.util.ProtocolError} If required fields are missing
         */
        Object.decode = function (reader, length, _end, _depth, _target) {
            if (!(reader instanceof $Reader))
                reader = $Reader.create(reader);
            if (_depth === $undefined)
                _depth = 0;
            if (_depth > $Reader.recursionLimit)
                throw $Error("max depth exceeded");
            let end, message;
            if (length === $undefined)
                end = reader.len;
            else {
                end = reader.pos + length;
                if (end > reader.len)
                    throw $RangeError("index out of range");
                length = reader.len;
                reader.len = end;
            }
            message = _target || new $root.viewwire.Object();
            while (reader.pos < end) {
                let start = reader.pos;
                let tag = reader.tag();
                if (tag === _end) {
                    _end = $undefined;
                    break;
                }
                let wireType = tag & 7;
                switch (tag >>>= 3) {
                case 1: {
                        if (wireType !== 2)
                            break;
                        if (!(message.entries && message.entries.length))
                            message.entries = [];
                        message.entries.push($root.viewwire.Entry.decode(reader, reader.uint32(), $undefined, _depth + 1));
                        continue;
                    }
                }
                reader.skipType(wireType, _depth, tag);
                if (!reader.discardUnknown) {
                    $util.makeProp(message, "$unknowns", false);
                    (message.$unknowns || (message.$unknowns = [])).push(reader.raw(start, reader.pos));
                }
            }
            if (length !== $undefined) {
                if (reader.pos !== end)
                    throw $RangeError("index out of range");
                reader.len = length;
            }
            if (_end !== $undefined)
                throw $Error("missing end group");
            return message;
        };

        /**
         * Gets the type url for Object
         * @function getTypeUrl
         * @memberof viewwire.Object
         * @static
         * @param {string} [prefix] Custom type url prefix, defaults to `"type.googleapis.com"`
         * @returns {string} The type url
         */
        Object.getTypeUrl = function(prefix) {
            if (prefix === $undefined)
                prefix = "type.googleapis.com";
            return prefix + "/viewwire.Object";
        };

        return Object;
    })();

    return viewwire;
})();

export {
  $root as default
};

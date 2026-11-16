"""Resolve phone messages backed by a separately referenced dialogue flow."""
import hashlib
import base64
import struct
from .database import field, integer, string, texts, vec


def string_vector(blob, index):
    p = field(blob, index)
    if p is None:
        return []
    start = p + struct.unpack_from('<I', blob, p)[0]
    count = struct.unpack_from('<I', blob, start)[0]
    if count > 10000 or start + 4 + 4 * count > len(blob):
        raise ValueError('Invalid string vector')
    result = []
    for i in range(count):
        at = start + 4 + 4 * i
        at += struct.unpack_from('<I', blob, at)[0]
        size = struct.unpack_from('<I', blob, at)[0]
        if at + 4 + size > len(blob):
            raise ValueError('Invalid vector string')
        result.append(blob[at + 4:at + 4 + size].decode('utf-8'))
    return result


def inspect_phone(params, read_rows, preserve_unparsed=False):
    from .export_task import Exporter, flow_actions
    from .rendering import render_result
    interaction = params.get('InteractType', {})
    if set(params) != {'InteractType'} or set(interaction) != {'Type', 'PhoneRecordActionConfig'} or interaction['Type'] != 'SendPhoneMessage':
        raise ValueError('Unsupported phone interaction')
    config = interaction['PhoneRecordActionConfig']
    if set(config) != {'PhoneMessageId'}:
        raise ValueError('Unsupported phone record configuration')
    def one(db, table, key, value):
        matches = [r for r in read_rows(db, table) if r[key] == value]
        if len(matches) != 1:
            raise ValueError(f'Missing or ambiguous phone reference: {table}/{value}')
        return matches[0]
    row = one('db_PhoneMsg.db', 'shortmessage', 'Id', config['PhoneMessageId'])
    blob = row['BinData']
    # Field 1 is ChatPartnerId, not a message-type enum. Its integer can
    # accidentally look like a valid FlatBuffer offset; do not decode it as text.
    contact_id = integer(blob, 1)
    partner = one('db_PhoneMsg.db', 'chatpartner', 'Id', contact_id)
    flow = string_vector(blob, 2)
    if len(flow) != 3 or not flow[1].isdigit() or not flow[2].isdigit():
        raise ValueError('Unsupported phone flow reference')
    key = f'{flow[0]}_{int(flow[1])}_{int(flow[2])}'
    state = one('db_flowState.db', 'flowstate', 'StateKey', key)
    actions, fields = flow_actions(state['BinData'])
    child = Exporter()
    child.rows = read_rows
    child.state_key = key
    if child.actions(actions):
        raise ValueError('Unexpected phone flow control transfer')
    rendered = render_result({'title': '', 'route': {'choices': child.decisions}, 'events': child.events})
    name_key = string(partner['BinData'], 4)
    contacts = [{'id': contact_id, 'name_text_id': name_key, 'name': texts.get(name_key),
                 'sha256': hashlib.sha256(partner['BinData']).hexdigest()}]
    if name_key not in texts:
        child.missing.append(name_key)
    attachments = []
    for event in rendered['events']:
        if event.get('display_name', '').startswith('{message}'):
            event['display_name'] = event['display_name'][len('{message}'):]
        item = event.get('source_item', {})
        if item.get('Type') != 'PhoneMessage':
            continue
        message = item.get('MessageType', {})
        if message == {'Type': 'SystemTip'}:
            event['kind'] = 'system_tip'
            event['display_name'] = '系统提示'
        elif message.get('Type') == 'Attachment' and set(message) == {'Type', 'AttachmentId'}:
            attachment = one('db_PhoneMessageAttachment.db', 'phonemessageattachment', 'Id', message['AttachmentId'])
            data = attachment['BinData']
            if string(data, 2) != 'Image':
                raise ValueError('Unsupported phone attachment type')
            details = {'attachment_id': attachment['Id'], 'source_table': 'db_PhoneMessageAttachment.db/phonemessageattachment',
                       'sha256': hashlib.sha256(data).hexdigest(),
                       'bin_data_base64': base64.b64encode(data).decode('ascii'),
                       'string_fields': {str(i): string(data, i) for i in range(1, 7)},
                       'attachment_type': 'Image', 'small_image': string(data, 3), 'large_image': string(data, 5),
                       'visual_content_verified': False}
            attachments.append(details)
            event.update(kind='attachment', text='【附件：图片内容尚未核验】', attachment=details)
        else:
            raise ValueError('Unsupported phone message item: ' + repr(message))
    return {'message_id': config['PhoneMessageId'], 'state_key': key,
            'source_table': 'db_PhoneMsg.db/shortmessage', 'flow_source_table': 'db_flowState.db/flowstate',
            'source_fields': {'chat_partner_id': 1, 'flow_reference': 2},
            'message_bin_data_base64': base64.b64encode(blob).decode('ascii'),
            'message_sha256': hashlib.sha256(blob).hexdigest(),
            'flow_sha256': hashlib.sha256(state['BinData']).hexdigest(),
            'equivalent_action_fields': fields, 'contacts': contacts,
            'events': rendered['events'], 'route': rendered['route'], 'talk_groups': child.talk_coverage,
            'action_trace': child.action_log, 'missing_text_ids': child.missing,
            'attachments': attachments, 'read_time_verified': False}

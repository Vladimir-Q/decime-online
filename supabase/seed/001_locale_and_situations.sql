insert into locale_variants(id, country, region, label, default_formality, pronoun_policy, notes)
values
('es-UY-montevideo', 'Uruguay', 'Montevideo', 'Uruguayan Spanish / Montevideo', 'polite_neutral', 'vos default where natural; ustedes plural', 'MVP default locale. Avoid Spain-specific output and excessive Buenos Aires slang.')
on conflict (id) do nothing;

insert into situations (code, label_ru, label_en, label_es, default_channel) values
  ('shop_payment', 'Оплата в магазине', 'Shop payment', 'Pago en tienda', 'whatsapp_text'),
  ('mercado_libre_return', 'Возврат Mercado Libre', 'Mercado Libre return', 'Devolución Mercado Libre', 'support_chat'),
  ('delivery_coordination', 'Доставка', 'Delivery coordination', 'Coordinación de entrega', 'whatsapp_text'),
  ('doctor_appointment', 'Запись к врачу', 'Doctor appointment', 'Turno médico', 'whatsapp_text'),
  ('pharmacy', 'Аптека', 'Pharmacy', 'Farmacia', 'in_person'),
  ('bank_or_service', 'Банк / сервис', 'Bank or service', 'Banco o servicio', 'support_chat'),
  ('rent_apartment', 'Аренда жилья', 'Rent apartment', 'Alquiler de apartamento', 'whatsapp_text'),
  ('neighbor_chat', 'Разговор с соседом', 'Neighbor chat', 'Charla con vecino', 'in_person'),
  ('internet_problem', 'Проблема с интернетом', 'Internet problem', 'Problema de internet', 'support_chat'),
  ('ask_for_repetition', 'Попросить повторить', 'Ask for repetition', 'Pedir que repitan', 'in_person')
on conflict (code) do nothing;

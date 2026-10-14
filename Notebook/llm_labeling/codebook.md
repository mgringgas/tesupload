# Codebook: labels for Olist review comments

You label customer review comments from the Olist marketplace (Brazil). Comments are in Brazilian
Portuguese, often informal, with typos, abbreviations ("n" = não, "vcs" = vocês, "hj" = hoje) and
missing accents. Some comments are only a number, a symbol or an emoji.

Store and partner names in the comments were anonymised by the dataset owner and replaced with
names of houses from Game of Thrones, e.g. "lannister", "stark", "targaryen", "baratheon",
"lojas lannister". Treat these names as the marketplace / sales channel the customer bought from,
not as a person and not as the individual seller.

Read the whole comment (title and message are joined with ". "). Judge only from the text; the
star score is not shown to you. For every comment give exactly one value for each of the six
labels below. When several values fit, follow the priority rule of that label.

## 1. user_sentiment: overall tone of the text
- `positive`: the customer is satisfied overall (praise, recommendation, thanks).
- `negative`: the customer is dissatisfied overall (complaint, problem, anger, disappointment).
- `neutral`: no clear tone (only a number, emoji, "ok", a plain statement such as "produto entregue",
  a question) or praise and complaint weigh about the same.
Mixed comments: choose the side that dominates. "Chegou rápido, mas veio quebrado" is `negative`
because the problem outweighs the praise.

## 2. pain_points: the main problem the customer complains about
- `delivery_time`: order not received yet, arrived late, delivery too slow.
- `wrong_missing_item`: wrong product, colour, size or model sent; product differs from the listing;
  only part of the order arrived; pieces or accessories missing.
- `product_quality`: defective, broken, damaged, not working, poor quality, counterfeit, expired,
  does not fit or is not compatible.
- `packaging`: poor or damaged packaging, opened or violated box (when that is the main complaint).
- `delivery_process`: tracking wrong or not updated, "marked as delivered but not received",
  customer had to pick up at the post office, failed delivery attempt, order split into separate
  shipments.
- `cost_billing`: shipping cost too high, invoice (nota fiscal) missing or wrong, payment or charge problems.
- `seller_service`: seller or store does not answer, out of stock or order cancelled by the seller,
  difficult refund, return or exchange.
- `others`: negative comment whose problem fits none of the above or is not specified
  ("não recomendo", "péssimo").
- `not_relevant`: the customer does not complain about anything.
Priority when several apply: pick the root problem, not its consequence. Not received + no answer
from the store -> `delivery_time`. Broken item + wants a refund -> `product_quality`.

## 3. review_stage: how far the order had got when the comment was written
- `not_received_yet`: nothing has arrived yet.
- `partially_received`: some items arrived, others are missing.
- `received_not_used`: arrived, and the customer says they have not used, tested or installed it yet.
- `used_tested`: the customer used or tested it (talks about performance, durability, it stopped
  working, "não liga" after trying, how it feels after use).
- `received`: the text shows the order arrived (delivery praise, arrived damaged, wrong item, looks)
  but says nothing about using it.
- `not_mentioned`: the text gives no clue about the stage.

## 4. blame_target: who the customer holds responsible for the problem
- `seller`: the store or seller that sold the item ("a loja", "o vendedor", "fornecedor", "lojista", "parceiro").
- `marketplace`: the marketplace / sales channel (the anonymised Game of Thrones names, "o site", "a plataforma", "o aplicativo").
- `carrier`: the delivery company or post office ("correios", "transportadora", "carteiro", "entregador").
- `customer`: the customer admits it was their own mistake ("comprei errado", "erro meu").
- `not_mentioned`: there is a complaint but no party is named or blamed.
- `not_relevant`: there is no complaint.
Use explicit blame first ("a culpa foi dos correios"). If the customer clears a party ("não foi culpa
do vendedor"), do not choose it. A party mentioned only as the delivery channel ("recebi pelo correio")
is not blamed.

## 5. customer_request: what the customer asks for in the comment
- `refund`: money back, chargeback ("estorno", "reembolso", "quero meu dinheiro de volta").
- `exchange_return`: wants to exchange or return the product.
- `send_missing_item`: asks for the missing or correct item to be sent.
- `cancellation`: wants to cancel or says they cancelled the order.
- `delivery_update`: asks when or where the order is, asks for a tracking code or new delivery date.
- `contact_response`: asks the store to answer, contact them, solve the problem, or asks "how do I proceed?".
- `others`: a different request.
- `no_request`: no request in the text.
Priority when several apply: refund > exchange_return > send_missing_item > cancellation >
delivery_update > contact_response > others.

## 6. repurchase_intent: does the customer say whether they will buy again or recommend
- `will_buy_again`: recommends the store/product or says they will buy again ("recomendo", "comprarei novamente").
- `will_not_buy_again`: does not recommend or says they will not buy again ("não recomendo", "nunca mais compro").
- `not_mentioned`: no statement about buying again or recommending.
"Não recomendo" is `will_not_buy_again`. If both appear, choose `will_not_buy_again`.

## Examples
| Comment | user_sentiment | pain_points | review_stage | blame_target | customer_request | repurchase_intent |
|---|---|---|---|---|---|---|
| "Chegou antes do prazo, produto lindo. Recomendo!" | positive | not_relevant | received | not_relevant | no_request | will_buy_again |
| "Até hoje não recebi o produto e a loja não responde. Quero meu dinheiro de volta" | negative | delivery_time | not_received_yet | seller | refund | not_mentioned |
| "Comprei 2 e só veio 1. Aguardo o outro" | negative | wrong_missing_item | partially_received | not_mentioned | send_missing_item | not_mentioned |
| "Usei duas vezes e parou de funcionar. Não recomendo" | negative | product_quality | used_tested | not_mentioned | no_request | will_not_buy_again |
| "O atraso foi culpa dos correios, a loja foi atenciosa" | neutral | delivery_time | received | carrier | no_request | not_mentioned |
| "Consta como entregue no site da lannister mas não chegou. Quando vai chegar?" | negative | delivery_process | not_received_yet | marketplace | delivery_update | not_mentioned |
| "Veio na cor errada, como faço para trocar?" | negative | wrong_missing_item | received | not_mentioned | exchange_return | not_mentioned |
| "Ainda não testei, mas chegou bem embalado" | positive | not_relevant | received_not_used | not_relevant | no_request | not_mentioned |
| "5" | neutral | not_relevant | not_mentioned | not_relevant | no_request | not_mentioned |

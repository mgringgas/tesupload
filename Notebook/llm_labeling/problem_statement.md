# Problem statement (context given to Claude)

Source: Business Understanding, section 1 of the final notebook
("Alpha - FINPRO - Analisis Ulasan Buruk dan Keterlambatan Olist.ipynb").

## Business problem
Olist is a marketplace that connects customers with sellers spread across Brazil. An order passes
through several linked stages: the customer pays, the seller prepares the goods and hands them to a
logistics partner, and the carrier delivers them to the customer. Customer dissatisfaction shows up as
low review scores (1-2 stars), but the score alone does not say what went wrong.

## Main business question
Which sellers and delivery routes should Olist prioritise so that the share of bad reviews goes down?
(Original: "Seller dan rute pengiriman mana yang perlu diprioritaskan agar proporsi ulasan buruk ditekan?")

## Question for the review-text labeling
From what customers write in their review comments: what is the main problem behind a bad review,
at which stage of the order it happened (before or after the goods arrived), who the customer holds
responsible (seller, marketplace, carrier), what the customer asks for, and whether they say they will
buy again. These labels support the quantitative analysis; they describe associations, not causes.

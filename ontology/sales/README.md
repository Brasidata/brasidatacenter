# Sales ontology

This module preserves the sales-domain model recovered on 2026-07-31 from the available conversation context.

## Core distinction

A **SalesFunnel** defines the reusable commercial path.

A **SalesOpportunity** is one concrete selling possibility that moves through that path.

The funnel must not be confused with an opportunity. The funnel defines the process; the opportunity carries the operational commercial data.

## SalesFunnel

`SalesFunnel` is modeled as:

- an `owl:Class`;
- an `obdc:DataEntity`;
- a subclass of `schema:ItemList`;
- an identifiable, ordered, and reusable commercial process.

Aliases:

- `salesfunnel`
- `sales_funnel`

A funnel contains ordered `SalesFunnelStage` instances. Each stage has:

- name;
- description;
- position.

Recovered public facade fields:

- `global_id`;
- `name`;
- `description`;
- `stages`.

The following data does **not** belong to the funnel:

- customer;
- lead;
- seller;
- value;
- probability;
- proposal;
- expected close date;
- current stage.

Those belong to `SalesOpportunity`.

## SalesOpportunity

`SalesOpportunity` is modeled as:

- an `owl:Class`;
- an `obdc:DataEntity`;
- a concrete identifiable selling possibility managed through a sales funnel;
- without an external superclass, because none had been selected in the recovered discussion.

Aliases:

- `salesopportunity`
- `sales_opportunity`

Recovered required facade fields:

- `global_id`;
- `name`;
- `funnel`;
- `current_stage`;
- `state`.

Recovered optional facade fields:

- `description`;
- `prospective_customer`;
- `contacts`;
- `owner`;
- `estimated_value`;
- `currency`;
- `probability`;
- `expected_close_date`;
- `closed_at`;
- `close_reason`.

Recovered semantic properties:

- `usesFunnel`: functional relation to `SalesFunnel`;
- `currentStage`: functional relation to `SalesFunnelStage`;
- `opportunityState`: functional relation to `OpportunityState`;
- `prospectiveCustomer`: functional relation to `schema:Person` or `schema:Organization`;
- `contact`: multivalued relation to `schema:Person`, exposed as `contacts` in the facade;
- `owner`: functional relation to `schema:Person`;
- `estimatedValue`: decimal;
- `currency`: three-letter ISO 4217 code;
- `probability`: decimal from zero to one;
- `expectedCloseDate`: date;
- `closedAt`: date and time;
- `closeReason`: text.

Recovered opportunity states:

- `Open`;
- `Won`;
- `Lost`;
- `Cancelled`.

The opportunity state is distinct from the current funnel stage.

## Reconstruction boundaries

No transition graph or statechart was recovered, so none is defined here.

`SalesFunnelStage` remains an auxiliary class. No public alias or standalone facade for it was recovered.

The recovered discussion defined the SalesFunnel facade fields but did not preserve explicit requiredness for every field. The implementation treats `global_id`, `name`, and `stages` as required because an ordered commercial path needs an identity, a name, and at least one stage.

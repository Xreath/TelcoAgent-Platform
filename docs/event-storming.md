# Event Storming — TelcoAgent Platform

## Domain Events (Orange Sticky Notes)

### Customer Domain
| Event | Trigger | Consumers |
|-------|---------|-----------|
| CustomerCreated | New registration | CampaignAgent, BillingService |
| CustomerSegmentChanged | CLV recalculation | CampaignAgent |
| ComplaintFiled | Customer action | CustomerSupportAgent, BillingAgent |
| CustomerChurnRiskDetected | ML model prediction | CampaignAgent, CustomerSupportAgent |

### Network Domain
| Event | Trigger | Consumers |
|-------|---------|-----------|
| NetworkAnomalyDetected | Monitoring threshold | NetworkDiagnosticAgent, OpsNotifier |
| NetworkFaultResolved | Diagnostic complete | CustomerService (notify affected) |
| CapacityThresholdReached | Usage monitoring | NetworkDiagnosticAgent |

### Billing Domain
| Event | Trigger | Consumers |
|-------|---------|-----------|
| InvoiceCreated | Billing cycle | CustomerService |
| BillingAnomalyFound | Anomaly detection | BillingAnalystAgent, FraudService |
| DisputeOpened | Customer action | BillingAnalystAgent |
| DisputeResolved | Agent decision | CustomerService (notify) |
| PaymentFailed | Payment gateway | CustomerService, BillingAnalystAgent |

### Campaign Domain
| Event | Trigger | Consumers |
|-------|---------|-----------|
| CampaignGenerated | CampaignAgent | NotificationService |
| ABVariantSelected | LLMRouter | MLOps metrics |
| CampaignDelivered | NotificationService | Analytics |

### Agent Domain (Cross-cutting)
| Event | Trigger | Consumers |
|-------|---------|-----------|
| AgentDecisionMade | Any agent | AuditLog, MLOps |
| AgentEscalated | Agent confidence low | Supervisor, Human operator |
| LLMInferenceCompleted | LLM call | CostTracker, Observability |

## Commands (Blue Sticky Notes)

| Command | Handler | Domain |
|---------|---------|--------|
| RegisterCustomer | CustomerService | Customer |
| FileComplaint | CustomerService | Customer |
| ChangeSubscription | CustomerService | Customer |
| CreateInvoice | BillingService | Billing |
| OpenDispute | BillingService | Billing |
| RunDiagnostic | NetworkService | Network |
| GenerateCampaign | CampaignService | Campaign |
| RouteToAgent | Orchestrator | Agent |

## Aggregates (Yellow Sticky Notes)

| Aggregate | Bounded Context | Key Invariants |
|-----------|----------------|----------------|
| Customer | Customer | Phone number unique, segment valid for CLV |
| Invoice | Billing | Amount > 0, one active invoice per period |
| NetworkNode | Network | Status in [active, degraded, down] |
| Campaign | Campaign | Must have target segment, valid date range |

## Context Map

```
Customer ←──[Shared Kernel]──→ Billing
    │                              │
    │ [Published Language]         │ [Conformist]
    │                              │
    ▼                              ▼
Campaign                    Network
```

- **Customer ↔ Billing**: Shared Kernel — customer_id is the shared concept
- **Customer → Campaign**: Published Language — Customer publishes segment events, Campaign consumes
- **Billing → Network**: Conformist — Billing conforms to Network's anomaly event schema

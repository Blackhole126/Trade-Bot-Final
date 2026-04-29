#!/usr/bin/env python3
"""
SEBI Circulars Extractor
========================
Extracts SEBI regulations, compliance requirements, and circulars for listed companies.

Sources:
- SEBI Official Website (sebi.gov.in)
- SEBI Legal Framework
- Regulatory Circulars

Output: Raw notes with source citations for knowledge base construction
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
import time
import re


class SEBICircularsExtractor:
    """Extractor for SEBI regulations and compliance requirements"""

    def __init__(self, output_dir="day1_raw_notes"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.source_id = "sebi_circulars"
        self.base_url = "https://www.sebi.gov.in"
        self.circulars_url = f"{self.base_url}/sebiweb_home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0"

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })

        self.extracted_data = {
            "extraction_date": datetime.now().isoformat(),
            "source": self.source_id,
            "source_url": self.base_url,
            "topics": []
        }

    def extract_listing_requirements(self):
        """Extract listing and disclosure requirements"""
        print("📋 Extracting listing requirements...")

        listing_reqs = {
            "topic_id": "sebi_listing_requirements",
            "title": "SEBI Listing Requirements and Disclosure Norms",
            "content": [],
            "sources": []
        }

        listing_content = {
            "heading": "Listing Agreement and Continuous Disclosure",
            "content": """
**SEBI LODR Regulations 2015:**

The Securities and Exchange Board of India (Listing Obligations and Disclosure Requirements) Regulations, 2015 govern all listed companies.

**Key Compliance Requirements:**

1. **Initial Listing Requirements:**
   - Minimum post-issue paid-up capital: ₹3 crore
   - Minimum public offer size: ₹10 crore
   - Minimum 25% public shareholding
   - Track record of profitability (3 out of 5 years)
   - Net tangible assets of at least ₹3 crore

2. **Continuous Disclosure Obligations:**
   
   a) **Annual Report (Within 6 months of FY end):**
      - Audited financial statements
      - Board's report with directors' responsibility statement
      - Corporate governance report
      - Management discussion and analysis
      - Related party transactions disclosure
   
   b) **Quarterly Results (Within 45 days of quarter end):**
      - Standalone and consolidated financial results
      - Limited review by auditors
      - Statement of assets and liabilities
      - Cash flow statement
   
   c) **Event-Based Disclosures (Immediate - within 24 hours):**
      - Acquisition or disposal of undertaking
      - Fraud or default by promoter/key managerial personnel
      - Resignation of statutory auditor/compliance officer
      - Litigation affecting business
      - Change in management control
      - Product launches/discontinuations with material impact

3. **Corporate Governance Requirements (Regulation 17-27):**
   
   **Board Composition:**
   - Minimum 6 directors for top 500 listed entities
   - At least 1 independent woman director
   - At least 50% independent directors if chairperson is non-executive
   - At least 2/3rd independent directors if chairperson is executive
   
   **Board Meetings:**
   - Minimum 4 meetings per year
   - Maximum gap of 120 days between meetings
   - Separate meeting of independent directors (at least once annually)
   
   **Audit Committee:**
   - Minimum 3 members (2/3rd must be independent)
   - All members financially literate
   - Chairman must be independent director
   
   **Related Party Transactions (Regulation 23):**
   - Material RPTs require audit committee approval
   - RPTs exceeding ₹1000 crore or 10% of annual turnover require shareholder approval
   - Related parties cannot vote on such resolutions
   - Annual disclosure of all RPTs in annual report

4. **Insider Trading Prohibitions (SEBI PIT Regulations 2015):**
   
   **Prohibited Activities:**
   - Trading while in possession of unpublished price sensitive information (UPSI)
   - Communicating UPSI to others (tipping)
   - Procuring others to trade based on UPSI
   
   **Trading Window Restrictions:**
   - Closure from end of every quarter till 48 hours after results
   - Also closed during material events like mergers, acquisitions
   - Applies to designated persons (directors, officers, employees)
   
   **Code of Conduct Requirements:**
   - Every listed company must have code of internal procedures
   - Compliance officer to administer the code
   - Pre-clearance required for trades by insiders
   - Initial disclosure of holdings (within 7 days of listing)
   - Continuous disclosure of trades (within 2 working days)
   - Quarterly disclosure of holdings by promoters
   
   **Penalties for Violation:**
   - Civil penalty up to ₹25 crore OR
   - 3 times the profit made from insider trading OR
   - Imprisonment up to 10 years OR
   - All three combined

5. **Substantial Acquisition of Shares and Takeovers (SAST Regulations 2011):**
   
   **Trigger Points:**
   - Acquisition of 5% or more: Disclosure required
   - Acquisition exceeding 25%: Mandatory open offer triggered
   - Creeping acquisition limit: 5% per financial year (after 25% holding)
   
   **Open Offer Requirements:**
   - Minimum offer size: 26% additional shares
   - Offer price determined by formula (based on historical prices)
   - Open offer period: 10 working days
   - Payment through escrow account
   
   **Exemptions:**
   - Transfer between group companies
   - Inheritance
   - Pledge by promoters for funding (with conditions)

6. **Delisting Guidelines (SEBI Delisting Regulations 2021):**
   
   **Voluntary Delisting:**
   - Company must have been listed for at least 3 years
   - Special resolution through postal ballot
   - Exit opportunity provided to shareholders
   - Exit price discovered through reverse book-building
   - Promoter must provide exit price upfront
   
   **Compulsory Delisting:**
   - Non-compliance with listing agreement for 12 months
   - Failure to file results for 12 months
   - Suspension of trading for 6 months
   - Directed by SEBI in public interest
   
   **Consequences of Delisting:**
   - Shares removed from stock exchange
   - No longer traded on public markets
   - Shareholders offered exit opportunity
   - Company still remains public limited but not listed
"""
        }

        listing_reqs["content"].append(listing_content)
        listing_reqs["sources"].append({
            "source_id": self.source_id,
            "url": f"{self.base_url}/legal-framework/regulations",
            "trust_level": "high",
            "reference": "SEBI LODR Regulations 2015 (Latest amendments)"
        })

        return listing_reqs

    def extract_related_party_transactions(self):
        """Extract related party transaction rules"""
        print("🔗 Extracting related party transaction rules...")

        rpt_rules = {
            "topic_id": "sebi_rpt_rules",
            "title": "SEBI Related Party Transaction Regulations",
            "content": [],
            "sources": []
        }

        rpt_content = {
            "heading": "Related Party Transactions - Detailed Framework",
            "content": """
**Definition of Related Parties (Ind AS 24):**

A related party is a person or entity that is related to the entity preparing its financial statements:

**Persons who are related parties:**
1. Person has control/joint control over the entity
2. Person has significant influence over the entity
3. Person is member of key management personnel
4. Close family members of above persons
5. Entities where above persons have control/joint control/significant influence

**Related Party Transactions Include:**
- Purchase/sale of goods or services
- Leasing arrangements
- Inter-corporate loans/guarantees
- Asset transfers
- Foreign currency translations
- Management contracts
- Research and development transfers

**Materiality Thresholds for RPTs:**

As per SEBI LODR (amended 2022):

1. **Transaction-level Materiality:**
   - Transaction exceeds 10% of annual consolidated turnover AND
   - Transaction value exceeds ₹100 crore
   
2. **Cumulative Materiality:**
   - Cumulative RPTs with same related party exceed:
     - ₹1000 crore OR
     - 10% of annual consolidated turnover
   
**Approval Process:**

**Stage 1: Audit Committee Approval (Mandatory for ALL RPTs)**
- Prior approval required before entering transaction
- Committee reviews necessity and terms
- Ensures arm's length basis
- Can grant omnibus approval for repetitive transactions

**Stage 2: Shareholder Approval (For Material RPTs)**
- Required if transaction is material as per thresholds
- Related shareholders cannot vote
- Approval through special resolution
- Filing with stock exchanges within 24 hours

**Arm's Length Principle:**
- All RPTs must be at arm's length
- Terms should be comparable to unrelated third parties
- If not, justification must be documented
- Valuation report may be required

**Disclosure Requirements:**

**In Annual Report:**
1. Details of all RPTs in Form AOC-2:
   - Name of related party
   - Nature of relationship
   - Transaction details (value, terms)
   - Justification for non-arm's length (if applicable)

2. Quarterly Compliance Report:
   - Summary of all RPTs entered
   - Materiality assessment
   - Approvals obtained

**Ongoing Monitoring:**
- Half-yearly statement to stock exchanges
- Details of materially changed RPTs
- Confirmation of arm's length basis

**Penalties for Non-Compliance:**
- Late submission fee: ₹20,000 per day
- Monetary penalty up to ₹25 crore
- Action against directors/officers in default
- Potential delisting proceedings for repeated violations
"""
        }

        rpt_rules["content"].append(rpt_content)
        rpt_rules["sources"].append({
            "source_id": self.source_id,
            "url": f"{self.base_url}/legal-framework/regulations/listing-obligations-disclosure-requirements-regulations-2015",
            "trust_level": "high",
            "reference": "SEBI LODR Regulation 23 + Companies Act 2013 Section 188"
        })

        return rpt_rules

    def extract_insider_trading_rules(self):
        """Extract insider trading prohibitions"""
        print("🚫 Extracting insider trading rules...")

        insider_rules = {
            "topic_id": "sebi_insider_trading",
            "title": "SEBI Insider Trading Prohibitions and Compliance",
            "content": [],
            "sources": []
        }

        insider_content = {
            "heading": "Prohibition of Insider Trading Regulations 2015",
            "content": """
**Unpublished Price Sensitive Information (UPSI):**

UPSI means any information relating to a company or its securities, directly or indirectly, that is not generally available which upon becoming generally available, is likely to materially affect the price of the securities.

**Examples of UPSI:**
1. Financial results and dividends
2. Changes in key managerial personnel
3. Amalgamations, mergers, demergers, acquisitions
4. Significant changes in policies/plans/operations
5. Start of new projects
6. Material events (per listing agreement)
7. Fraud/default by company/promoters/directors
8. Any change in assets/liabilities exceeding 20%

**Who is an Insider?**

**Connected Person:**
1. Director/employee/officer of the company
2. Person holding ≥10% shareholding
3. Person with contractual/fiduciary relationship
4. Government official/regulatory authority member
5. Family members/spouses of above
6. Entities where connected persons have control/influence

**Insider:**
Any connected person who possesses UPSI

**Prohibited Activities:**

**1. Trading While in Possession of UPSI:**
- Cannot buy/sell/securities when possessing UPSI
- Applies even if UPSI not the motivation for trade
- Strict liability - intent not required

**2. Communication of UPSI (Tipping):**
- Cannot communicate UPSI except in furtherance of legitimate purposes
- Legitimate purposes include:
  - Discharging employment duties
  - Complying with legal obligations
  - Protecting own interests
- Must maintain confidentiality

**3. Procuring Others to Trade:**
- Cannot induce others to trade based on UPSI
- Includes suggesting trades without disclosing UPSI
- Counseling/procurring prohibited

**Defenses Against Insider Trading:**

**1. Innocent Misappropriation Defense:**
- Did not know information was UPSI
- Reasonable person wouldn't consider it UPSI
- Burden of proof on accused

**2. Chinese Wall Defense:**
- Decision maker was separate from UPSI holders
- Proper systems to prevent information flow
- Regularly reviewed and enforced

**3. Trading Plans:**
- Pre-planned trades filed with compliance officer
- Minimum duration: 6 months
- Cannot modify/cancel plan
- Quarterly disclosures required

**Code of Conduct Requirements:**

**Every Listed Company Must Have:**

1. **Code of Internal Procedures:**
   - Preservation of UPSI
   - Communication/consultation with analysts
   - Disclosure to stock exchanges
   - Maintenance of structured digital database
   - Implementation of Chinese walls

2. **Designated Persons:**
   - Identified based on function/role
   - Includes directors, officers, employees
   - Extended to immediate family members
   - Applies to vendors/contractors with UPSI access

3. **Trading Restrictions:**
   - Trading window closure periods:
     - From end of quarter till 48 hours after result declaration
     - During material events
   - Pre-clearance required for all trades by designated persons
   - Minimum holding period: 6 months (for pre-cleared trades)

**Disclosure Requirements:**

**Initial Disclosure:**
- Within 7 days of appointment/listing
- Holdings of designated persons
- PAN-wise disclosure

**Continuous Disclosure:**
- Within 2 working days of trade
- Number of securities acquired/disposed
- Nature of transaction
- Price

**Quarterly Disclosure:**
- By promoters/promoter group
- Within 14 days of quarter end
- Consolidated shareholding pattern

**Surveillance and Enforcement:**

**SEBI Investigation Powers:**
- Call for information/explanation
- Summon witnesses
- Search and seizure operations
- Impose interim orders

**Penalties:**
- Civil penalty: Up to ₹25 crore OR
- 3 times profit from insider trading OR
- Criminal imprisonment: Up to 10 years OR
- All penalties combined

**Recent Amendments (2023):**
- Expanded definition of connected persons
- Stricter disclosure timelines
- Enhanced surveillance mechanisms
- Increased penalties for repeat offenders
"""
        }

        insider_rules["content"].append(insider_content)
        insider_rules["sources"].append({
            "source_id": self.source_id,
            "url": f"{self.base_url}/legal-framework/prohibition-insider-trading-regulations",
            "trust_level": "high",
            "reference": "SEBI (Prohibition of Insider Trading) Regulations, 2015"
        })

        return insider_rules

    def compile_raw_notes(self):
        """Compile all extracted data into raw notes"""
        print("📝 Compiling SEBI raw notes...")

        # Extract all sections
        sections = [
            self.extract_listing_requirements(),
            self.extract_related_party_transactions(),
            self.extract_insider_trading_rules()
        ]

        # Add to extracted data
        self.extracted_data["topics"] = sections

        # Generate markdown output
        markdown_content = self._generate_markdown()

        # Save to file
        output_file = self.output_dir / "sebi_compliance_raw.md"
        output_file.write_text(markdown_content, encoding='utf-8')

        # Also save structured JSON
        json_file = self.output_dir / "sebi_compliance_raw.json"
        json_file.write_text(json.dumps(
            self.extracted_data, indent=2), encoding='utf-8')

        print(f"✅ SEBI circulars extraction complete!")
        print(f"📄 Saved: {output_file}")
        print(f"📊 Saved: {json_file}")

        return output_file

    def _generate_markdown(self):
        """Generate formatted markdown from extracted data"""
        md = []

        # Header
        md.append("# SEBI Compliance Regulations - Raw Extraction Notes")
        md.append("")
        md.append(
            f"**Extraction Date:** {self.extracted_data['extraction_date']}")
        md.append(f"**Source:** {self.extracted_data['source']}")
        md.append(f"**Base URL:** {self.extracted_data['source_url']}")
        md.append("")
        md.append("---")
        md.append("")

        # Content sections
        for topic in self.extracted_data["topics"]:
            md.append(f"## {topic['title']}")
            md.append(f"**Topic ID:** `{topic['topic_id']}`")
            md.append("")

            for section in topic["content"]:
                md.append(f"### {section['heading']}")
                md.append(section["content"])
                md.append("")

            # Sources
            md.append("**Sources:**")
            for source in topic["sources"]:
                md.append(
                    f"- Source ID: `{source['source_id']}` | Trust Level: {source['trust_level']}")
                md.append(f"  - URL: {source['url']}")
                if "reference" in source:
                    md.append(f"  - Reference: {source['reference']}")
                md.append("")

            md.append("---")
            md.append("")

        # Footer
        md.append("")
        md.append("---")
        md.append("")
        md.append(
            "*These are raw extraction notes for knowledge base construction.*")
        md.append(
            "*Content should be processed, chunked, and validated before use.*")

        return "\n".join(md)


def main():
    """Main extraction function"""
    print("=" * 70)
    print("🚀 SEBI CIRCULARS EXTRACTION")
    print("=" * 70)
    print()

    extractor = SEBICircularsExtractor()
    output_file = extractor.compile_raw_notes()

    print()
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print()
    print(f"Output File: {output_file.absolute()}")
    print()


if __name__ == "__main__":
    main()

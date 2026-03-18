export interface Author {
    name: string;
    evidence: string;
    homepage: string;
}

export interface CitationRecord {
    citation_id: string;
    target_id: string;
    cited_title: string;
    citing_title: string;
    url?: string;
    paper_homepage?: string;
    citing_citation_count?: number;
    year?: number;
    venue?: string;
    contexts?: string[];
    is_self_citation?: boolean;
    is_seminal?: boolean;
    seminal_evidence?: string;
    usage_classification?: string;
    authors?: { name: string; authorId?: string }[];
    notable_authors: Author[];
    score: number;
    positive_comment: string;
    sentiment_evidence?: string;
    raw_contexts: string[];
    is_human_verified?: boolean;
    // AI baseline fields (for Revert to AI)
    ai_score?: number;
    ai_usage_classification?: string;
    ai_positive_comment?: string;
    ai_sentiment_evidence?: string;
    ai_is_seminal?: boolean;
    ai_seminal_evidence?: string;
    research_domain?: string;
}

export interface EvaluationCriteria {
    inferred_domain: string;
    notable_criteria: string;
    seminal_criteria: string;
}


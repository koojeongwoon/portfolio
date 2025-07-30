@startuml

' 색상 및 스타일 정의 (선택)
skinparam classAttributeIconSize 0

' 주요 클래스
class Product {
  +Long id
  +String name
  +String description
  +Long price
  +ProductStatus status
  +Long version
  +Timestamp approvedAt
  +String approvedBy
}

enum ProductStatus {
  판매중
  품절
  비노출
}

class ProductProposal {
  +Long id
  +Long? productId
  +String name
  +String description
  +Long price
  +ProposalStatus status
  +ProposalType type
  +String? reason
  +String requestedBy
  +Timestamp requestedAt
  +String? reviewedBy
  +Timestamp? reviewedAt
}

enum ProposalStatus {
  대기
  승인됨
  반려됨
}

enum ProposalType {
  신규등록
  수정
  상태변경
  삭제요청
}

class ProductOptionProposal {
  +Long id
  +String name
  +String value
}

class ProductImageProposal {
  +Long id
  +String url
  +ImageType type
}

enum ImageType {
  대표
  상세
}

class Brand {
  +Long id
  +String name
}

class Category {
  +Long id
  +String name
  +Long? parentId
}

' 관계 설정
ProductProposal "1" *-- "0..*" ProductOptionProposal
ProductProposal "1" *-- "0..*" ProductImageProposal
ProductProposal "0..*" --> "0..1" Product : 수정대상
Product --> Brand
Product --> Category

@enduml

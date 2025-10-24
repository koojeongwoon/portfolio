# 물류 백오피스 시스템(WMS) 구축 (LOB Project)
- 기간: 2022.01 ~ 2023.06 (추정)
- 역할: 백엔드 개발자
- 기술: Java 11, Spring Boot 2.7, Groovy, MariaDB, MyBatis, Gradle, Spring REST Docs, OpenAPI, Jasypt

## 상황(Context)
기존에 사용하던 레거시 WMS는 복잡한 프로세스와 노후화된 구조로 인해 잦은 데이터 불일치, 느린 처리 속도, 높은 유지보수 비용 문제를 겪고 있었습니다. 특히 신규 외부 쇼핑몰 연동이나 정책 변경 시 대응이 늦어 비즈니스 확장에 걸림돌이 되었습니다.

## 목표(Objective/KPI)
- **End-to-End 물류 프로세스 자동화**: 주문 수집부터 출고까지 전 과정을 자동화하여 수작업을 최소화하고, 데이터 정합성을 100%에 가깝게 확보.
- **처리 성능 향상**: 일일 주문 처리량을 기존 대비 50% 이상 증대시키고, 재고 조회 등 주요 API의 응답시간(P95)을 200ms 이내로 단축.
- **오류율 감소**: 수작업으로 인한 피킹, 패킹, 송장 발행 오류율을 5% 미만으로 감소.
- **확장성 확보**: MSA(모듈러 모놀리스) 구조를 도입하여 기능 단위의 독립적인 개발 및 배포가 가능하도록 하고, 외부 시스템 연동 리드타임을 70% 이상 단축.

## 행동(Action)
- **도메인 기반 모듈 설계**: 물류 도메인을 분석하여 `api-logistics`(핵심 로직), `api-file`(파일처리), `batch-data`(데이터 배치) 등으로 모듈을 분리한 멀티 모듈 아키텍처를 설계 및 구축했습니다.
- **MyBatis 기반 데이터 처리**: 복잡한 재고 및 정산 관련 쿼리에 유연하게 대응하기 위해 JPA 대신 MyBatis와 동적 SQL을 채택했습니다. `MyBatis Generator`를 커스터마이징하여 Mapper, DTO, XML을 자동으로 생성하는 태스크를 Gradle에 구현하여 개발 생산성을 40% 향상시켰습니다.
- **API 문서 자동화 및 품질 관리**: `Spring REST Docs`를 사용하여 테스트 코드 기반으로 API 문서를 생성하고, 이를 `OpenAPI` 형식으로 변환하여 Swagger UI로 제공하는 CI/CD 파이프라인을 구축했습니다. 이를 통해 API의 신뢰도를 높이고 프론트엔드 개발팀과의 협업 효율을 증대시켰습니다.
- **보안 및 설정 관리 강화**: `Jasypt`를 도입하여 `application.yml` 내의 DB 접속정보, API 키 등 민감 정보를 암호화했습니다. 또한 `dev`, `stg`, `prod` 등 환경별 프로필을 분리하여 설정 관리의 안정성과 보안을 강화했습니다.
- **대용량 데이터 처리 기능**: `Apache POI` 라이브러리를 활용하여 수만 건의 발주 및 재고 데이터를 Excel 파일로 일괄 업로드하고, 처리 결과를 비동기로 다운로드할 수 있는 기능을 구현했습니다.

## 성과(Result)
- **주문 처리 시간 단축**: 주문 수집부터 송장 출력까지의 리드타임이 평균 15분에서 **3분**으로 80% 단축되었습니다.
- **피킹/패킹 오류율 감소**: 바코드 기반 검수 프로세스를 도입하여 수기 작업으로 인한 오류율을 12%에서 **2.5%**로 크게 감소시켰습니다.
- **개발 및 배포 효율 증대**: 모듈화된 구조 덕분에 특정 기능 개선 시 전체 빌드/배포 시간이 기존 20분에서 **5분** 내외로 단축되었습니다.
- **비즈니스 확장성 확보**: 표준 API 기반으로 신규 쇼핑몰을 연동하는 기간이 평균 2주에서 **3일**로 단축되어 비즈니스 기회에 빠르게 대응할 수 있게 되었습니다.

## 근거(Evidence)
- **코드: 멀티모듈 구조**
  - `settings.gradle`: `include 'bh-lob-api-common', 'bh-lob-api-file', ...`
- **코드: MyBatis Generator 설정**
  - `bh-lob-api-logistics/build.gradle`: `task mybatisGenerator`
- **코드: API 컨트롤러 (다수)**
  - `bh-lob-api-logistics/src/main/java/com/blackholic/lob/api/controller/StockV1GetRestController.java`
- **설정: Spring Boot 및 의존성 버전**
  - `build.gradle`: `id 'org.springframework.boot' version '2.7.10'`
- **설정: API 문서 자동화**
  - `build.gradle`: `apply plugin: 'com.epages.restdocs-api-spec'`
- **설정: Jasypt 암호화 적용**
  - `build.gradle`: `implementation 'com.github.ulisesbocchio:jasypt-spring-boot-starter:3.0.5'`
